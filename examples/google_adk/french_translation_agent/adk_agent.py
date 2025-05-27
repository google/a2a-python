import os
from google.adk.agents import LlmAgent

async def create_french_translation_agent() -> LlmAgent:
    """Constructs the ADK French Translation agent."""
    # Ensure GOOGLE_API_KEY is set for Gemini model usage.
    if not os.getenv("GOOGLE_API_KEY"):
        print("Warning: GOOGLE_API_KEY environment variable not set. This agent may not function correctly.")

    return LlmAgent(
        model='gemini-1.5-flash',
        name='french_translation_agent_adk',
        description='An agent that translates text to French.',
        instruction="""You are a translation assistant. The user will provide text.
Translate the provided text into French.
Only return the translated French text. Do not include any other commentary or explanations.
Example: If the user provides "Hello, how are you?", you should return "Bonjour, comment ça va ?"
""",
        tools=[],
    )
