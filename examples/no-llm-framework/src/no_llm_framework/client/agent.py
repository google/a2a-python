import asyncio
import json
import re
from collections.abc import Callable, Generator
from pathlib import Path
from typing import Literal
from uuid import uuid4

import google.generativeai as genai
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
    TaskStatusUpdateEvent,
    TextPart,
)
from jinja2 import Template

from no_llm_framework.client.constant import GOOGLE_API_KEY


dir_path = Path(__file__).parent

with Path(dir_path / 'decide.jinja').open('r') as f:
    decide_template = Template(f.read())

with Path(dir_path / 'agents.jinja').open('r') as f:
    agents_template = Template(f.read())

with Path(dir_path / 'agent_answer.jinja').open('r') as f:
    agent_answer_template = Template(f.read())


def stream_llm(prompt: str) -> Generator[str]:
    """Stream LLM response.

    Args:
        prompt (str): The prompt to send to the LLM.

    Returns:
        Generator[str, None, None]: A generator of the LLM response.
    """
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    for chunk in model.generate_content(prompt, stream=True):
        yield chunk.text


class Agent:
    """Agent for interacting with the Google Gemini LLM in different modes."""

    def __init__(
        self,
        mode: Literal['complete', 'stream'] = 'stream',
        token_stream_callback: Callable[[str], None] | None = None,
        agent_urls: list[str] | None = None,
        agent_prompt: str | None = None,
    ):
        self.mode = mode
        self.token_stream_callback = token_stream_callback
        self.agent_urls = agent_urls
        self.agents_registry: dict[str, AgentCard] = {}

    async def get_agents(self) -> tuple[dict[str, AgentCard], str]:
        """Retrieve agent cards from all agent URLs and render the agent prompt.

        Returns:
            tuple[dict[str, AgentCard], str]: A dictionary mapping agent names to AgentCard objects, and the rendered agent prompt string.
        """  # noqa: E501
        async with httpx.AsyncClient() as httpx_client:
            card_resolvers = [
                A2ACardResolver(httpx_client, url) for url in self.agent_urls
            ]
            agent_cards = await asyncio.gather(
                *[
                    card_resolver.get_agent_card()
                    for card_resolver in card_resolvers
                ]
            )
            agents_registry = {
                agent_card.name: agent_card for agent_card in agent_cards
            }
            agent_prompt = agents_template.render(agent_cards=agent_cards)
            return agents_registry, agent_prompt

    def call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt and return the response as a string or generator.

        Args:
            prompt (str): The prompt to send to the LLM.

        Returns:
            str or Generator[str]: The LLM response as a string or generator, depending on mode.
        """  # noqa: E501
        if self.mode == 'complete':
            return stream_llm(prompt)

        result = ''
        for chunk in stream_llm(prompt):
            result += chunk
        return result

    async def decide(
        self,
        question: str,
        agents_prompt: str,
        called_agents: list[dict] | None = None,
    ) -> Generator[str, None]:
        """Decide which agent(s) to use to answer the question.

        Args:
            question (str): The question to answer.
            agents_prompt (str): The prompt describing available agents.
            called_agents (list[dict] | None): Previously called agents and their answers.

        Returns:
            Generator[str, None]: The LLM's response as a generator of strings.
        """  # noqa: E501
        if called_agents:
            call_agent_prompt = agent_answer_template.render(
                called_agents=called_agents
            )
        else:
            call_agent_prompt = ''
        prompt = decide_template.render(
            question=question,
            agent_prompt=agents_prompt,
            call_agent_prompt=call_agent_prompt,
        )
        return self.call_llm(prompt)

    def extract_agents(self, response: str) -> list[dict]:
        """Extract the agents from the response.

        Args:
            response (str): The response from the LLM.
        """
        pattern = r'```json\n(.*?)\n```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return []

    async def send_message_to_an_agent(
        self, agent_card: AgentCard, message: str
    ):
        """Send a message to a specific agent and yield the streaming response.

        Args:
            agent_card (AgentCard): The agent to send the message to.
            message (str): The message to send.

        Yields:
            str: The streaming response from the agent.
        """
        async with httpx.AsyncClient() as httpx_client:
            client = A2AClient(httpx_client, agent_card=agent_card)
            message = MessageSendParams(
                message=Message(
                    role=Role.user,
                    parts=[Part(TextPart(text=message))],
                    messageId=uuid4().hex,
                    taskId=uuid4().hex,
                )
            )

            streaming_request = SendStreamingMessageRequest(params=message)
            async for chunk in client.send_message_streaming(streaming_request):
                if isinstance(
                    chunk.root, SendStreamingMessageSuccessResponse
                ) and isinstance(chunk.root.result, TaskStatusUpdateEvent):
                    message = chunk.root.result.status.message
                    if message:
                        yield message.parts[0].root.text

    async def stream(self, question: str):
        """Stream the process of answering a question, possibly involving multiple agents.

        Args:
            question (str): The question to answer.

        Yields:
            str: Streaming output, including agent responses and intermediate steps.
        """  # noqa: E501
        agent_answers: list[dict] = []
        for _ in range(3):
            agents_registry, agent_prompt = await self.get_agents()
            response = ''
            for chunk in await self.decide(
                question, agent_prompt, agent_answers
            ):
                response += chunk
                if self.token_stream_callback:
                    self.token_stream_callback(chunk)
                yield chunk

            agents = self.extract_agents(response)
            if agents:
                for agent in agents:
                    agent_response = ''
                    agent_card = agents_registry[agent['name']]
                    yield f'<Agent name="{agent["name"]}">\n'
                    async for chunk in self.send_message_to_an_agent(
                        agent_card, agent['prompt']
                    ):
                        agent_response += chunk
                        if self.token_stream_callback:
                            self.token_stream_callback(chunk)
                        yield chunk
                    yield '</Agent>\n'
                    match = re.search(
                        r'<Answer>(.*?)</Answer>', agent_response, re.DOTALL
                    )
                    answer = match.group(1).strip() if match else agent_response
                    agent_answers.append(
                        {
                            'name': agent['name'],
                            'prompt': agent['prompt'],
                            'answer': answer,
                        }
                    )
            else:
                return


if __name__ == '__main__':
    import asyncio
    import colorama

    async def main():
        """Main function to run the A2A Repo Agent client."""
        agent = Agent(
            mode='stream',
            token_stream_callback=None,
            agent_urls=['http://localhost:9999/'],
        )

        async for chunk in agent.stream('What is A2A protocol?'):
            if chunk.startswith('<Agent name="'):
                print(colorama.Fore.CYAN + chunk, end='', flush=True)
            elif chunk.startswith('</Agent>'):
                print(colorama.Fore.RESET + chunk, end='', flush=True)
            else:
                print(chunk, end='', flush=True)

    asyncio.run(main())
