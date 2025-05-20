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
        if self.mode == 'complete':
            return stream_llm(prompt)

        result = ''
        for chunk in stream_llm(prompt):
            result += chunk
        return result

    async def decide(
        self, question: str, agents_prompt: str
    ) -> Generator[str, None]:
        prompt = decide_template.render(
            question=question, agent_prompt=agents_prompt
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
        agents_registry, agent_prompt = await self.get_agents()
        response = ''
        for chunk in await self.decide(question, agent_prompt):
            response += chunk
            if self.token_stream_callback:
                self.token_stream_callback(chunk)
            yield chunk

        agents = self.extract_agents(response)
        agent_answers: list[dict] = []
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
            if answer:
                agent_answers.append(
                    {
                        'name': agent['name'],
                        'prompt': agent['prompt'],
                        'answer': answer,
                    }
                )
            else:
                print('<Answer> tag not found')
        print(agent_answers)


if __name__ == '__main__':
    import asyncio
    import colorama

    async def main():
        agent = Agent(
            mode='stream',
            token_stream_callback=None,
            agent_urls=['http://localhost:9999/'],
        )
        agents_registry, agent_prompt = await agent.get_agents()
        # agent_card = agents_registry['A2A Protocol Agent']
        async for chunk in agent.stream('What is A2A protocol?'):
            if chunk.startswith('<Agent name="'):
                print(colorama.Fore.CYAN + chunk, end='', flush=True)
            elif chunk.startswith('</Agent>'):
                print(colorama.Fore.RESET + chunk, end='', flush=True)
            else:
                print(chunk, end='', flush=True)
        # async for chunk in stream_response:
        #     print(chunk, end='', flush=True)

    asyncio.run(main())
