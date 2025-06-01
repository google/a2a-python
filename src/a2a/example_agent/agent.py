import os
import google.generativeai as genai

# Placeholder classes - replace with actual imports from a2a.sdk when available
class Agent:
    def __init__(self, capabilities):
        self.capabilities = capabilities

class AgentCapability:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters

class TaskCompleter:
    def complete_task(self, output):
        raise NotImplementedError

    def fail_task(self, error_message):
        raise NotImplementedError

class TaskParameters:
    def __init__(self, parameters):
        self._parameters = parameters

    def get(self, key: str, default: any = None) -> any:
        return self._parameters.get(key, default)

# End of placeholder classes

from a2a.types import AgentCapabilities  # Assuming AgentCapabilities is available
# from a2a.server.task_queue import TaskParameters # Assuming TaskParameters is available


class ExampleAgent(Agent):
    """An example agent that echoes back the input."""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=self.api_key)

        super().__init__(
            capabilities=AgentCapabilities(
                initial_prompt="You are a helpful AI assistant that can write blog posts.",
                capabilities=[
                    AgentCapability(
                        name="generate_blog_topic",
                        description="Generates a blog post topic based on provided keywords.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Keywords to base the topic on.",
                                },
                            },
                            "required": ["keywords"],
                        },
                    ),
                    AgentCapability(
                        name="generate_blog_outline",
                        description="Generates a blog post outline for a given topic.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "The topic of the blog post.",
                                },
                            },
                            "required": ["topic"],
                        },
                    ),
                    AgentCapability(
                        name="write_blog_section",
                        description="Writes content for a specific blog section using a Gemini model.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "section_prompt": {
                                    "type": "string",
                                    "description": "The prompt or title for the blog section.",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "The Gemini model to use (e.g., 'gemini-1.5-flash-latest'). Defaults to 'gemini-1.5-flash-latest'.",
                                    "default": "gemini-1.5-flash-latest",
                                }
                            },
                            "required": ["section_prompt"],
                        },
                    ),
                    AgentCapability(
                        name="assemble_blog_post",
                        description="Assembles the title and sections into a formatted blog post.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The title of the blog post.",
                                },
                                "sections": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "The written content of each blog section.",
                                },
                            },
                            "required": ["title", "sections"],
                        },
                    ),
                     AgentCapability(
                        name="echo", # Keep the echo capability for basic testing
                        description="Echoes back the input.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The message to echo.",
                                },
                            },
                            "required": ["message"],
                        },
                    )
                ],
            )
        )
        self.model_text = genai.GenerativeModel('gemini-1.5-flash-latest') # Default model for text

    async def _call_gemini_api(self, prompt: str, model_name: str) -> str:
        try:
            model_to_use = genai.GenerativeModel(model_name)
            response = await model_to_use.generate_content_async(prompt)
            return response.text
        except Exception as e:
            # Log the exception e
            print(f"Error calling Gemini API: {e}")
            # Consider how to propagate this error or handle it,
            # for now, returning an error message in the content.
            return f"Error generating content: {str(e)}"

    async def generate_blog_topic(self, keywords: list[str]) -> str:
        prompt = f"Generate a compelling blog post topic based on the following keywords: {', '.join(keywords)}. Provide only the topic text."
        return await self._call_gemini_api(prompt, self.model_text.model_name)

    async def generate_blog_outline(self, topic: str) -> list[str]:
        prompt = f"Generate a blog post outline (list of main sections) for the topic: '{topic}'. Return the outline as a numbered list. Each section on a new line."
        response_text = await self._call_gemini_api(prompt, self.model_text.model_name)
        # Simple parsing for numbered list. Robust parsing might be needed.
        return [line.strip() for line in response_text.splitlines() if line.strip()]


    async def write_blog_section(self, section_prompt: str, model: str) -> str:
        prompt = f"Write a detailed blog post section for the following prompt/title: '{section_prompt}'."
        return await self._call_gemini_api(prompt, model)

    def assemble_blog_post(self, title: str, sections: list[str]) -> str:
        post = f"# {title}\n\n"
        for i, section_content in enumerate(sections):
            # Assuming sections might already have their own subheadings or are just paragraphs
            post += f"{section_content}\n\n"
        return post.strip()

    async def execute_task(
        self,
        task_completer: TaskCompleter,
        parameters: TaskParameters,
        # TODO: Add type hint for function_to_call
        # function_to_call: FunctionToCallBase, # Still a TODO
    ):
        # capability_name = function_to_call.name
        capability_name = parameters.get("capability_name") # Expect capability_name in parameters for now

        try:
            if capability_name == "echo":
                message = parameters.get("message", "No message provided.")
                task_completer.complete_task(output=message)
            elif capability_name == "generate_blog_topic":
                keywords = parameters.get("keywords", [])
                if not keywords:
                    task_completer.fail_task(error_message="Keywords are required for generate_blog_topic.")
                    return
                output = await self.generate_blog_topic(keywords=keywords)
                task_completer.complete_task(output=output)
            elif capability_name == "generate_blog_outline":
                topic = parameters.get("topic")
                if not topic:
                    task_completer.fail_task(error_message="A topic is required for generate_blog_outline.")
                    return
                output = await self.generate_blog_outline(topic=topic)
                task_completer.complete_task(output=output)
            elif capability_name == "write_blog_section":
                section_prompt = parameters.get("section_prompt")
                model = parameters.get("model", self.model_text.model_name)
                if not section_prompt:
                    task_completer.fail_task(error_message="A section_prompt is required for write_blog_section.")
                    return
                output = await self.write_blog_section(section_prompt=section_prompt, model=model)
                task_completer.complete_task(output=output)
            elif capability_name == "assemble_blog_post":
                title = parameters.get("title")
                sections = parameters.get("sections", [])
                if not title or not sections:
                    task_completer.fail_task(error_message="Title and sections are required for assemble_blog_post.")
                    return
                output = self.assemble_blog_post(title=title, sections=sections)
                task_completer.complete_task(output=output)
            else:
                task_completer.fail_task(error_message=f"Unknown capability: {capability_name}")
        except Exception as e:
            # Log e
            print(f"Error during task execution for {capability_name}: {e}")
            task_completer.fail_task(error_message=f"Error executing {capability_name}: {str(e)}")
