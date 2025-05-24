import asyncio
import json
import re
from collections.abc import AsyncGenerator, Callable, Generator
from pathlib import Path
from typing import Literal

import google.generativeai as genai
from jinja2 import Template
from mcp.types import CallToolResult

from no_llm_framework.server.constant import GOOGLE_API_KEY
from no_llm_framework.server.mcp import call_mcp_tool, get_mcp_tool_prompt

dir_path = Path(__file__).parent

with Path(dir_path / 'decide.jinja').open('r') as f:
    decide_template = Template(f.read())

with Path(dir_path / 'tool.jinja').open('r') as f:
    tool_template = Template(f.read())

with Path(dir_path / 'called_tools_history.jinja').open('r') as f:
    called_tools_history_template = Template(f.read())


def stream_llm(prompt: str) -> Generator[str, None]:
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
        mcp_url: str | None = None,
    ):
        self.mode = mode
        self.token_stream_callback = token_stream_callback
        self.mcp_url = mcp_url

    def call_llm(self, prompt: str) -> Generator[str, None]:
        """Call the LLM with the given prompt and return a generator of responses.

        Args:
            prompt (str): The prompt to send to the LLM.

        Returns:
            Generator[str, None]: A generator yielding the LLM's response.
        """   # noqa: E501
        return stream_llm(prompt)

    async def decide(
        self, question: str, called_tools: list[dict] | None = None
    ) -> Generator[str, None]:
        """Decide which tool to use to answer the question.

        Args:
            question (str): The question to answer.
            called_tools (list[dict]): The tools that have been called.
        """
        if self.mcp_url is None:
            return self.call_llm(question)
        tool_prompt = await get_mcp_tool_prompt(self.mcp_url)
        if called_tools:
            called_tools_prompt = called_tools_history_template.render(
                called_tools=called_tools
            )
        else:
            called_tools_prompt = ''

        prompt = decide_template.render(
            question=question,
            tool_prompt=tool_prompt,
            called_tools=called_tools_prompt,
        )
        return self.call_llm(prompt)

    def extract_tools(self, response: str) -> list[dict]:
        """Extract the tools from the response.

        Args:
            response (str): The response from the LLM.
        """
        pattern = r'```json\n(.*?)\n```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return []

    async def call_tool(self, tools: list[dict]) -> list[CallToolResult]:
        """Call the tool.

        Args:
            tools (list[dict]): The tools to call.
        """
        return await asyncio.gather(
            *[
                call_mcp_tool(self.mcp_url, tool['name'], tool['arguments'])
                for tool in tools
            ]
        )

    async def stream(self, question: str) -> AsyncGenerator[str]:
        """Stream the process of answering a question, possibly involving tool calls.

        Args:
            question (str): The question to answer.

        Yields:
            dict: Streaming output, including intermediate steps and final result.
        """  # noqa: E501
        called_tools = []
        for i in range(10):
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': f'Step {i}',
            }

            response = ''
            for chunk in await self.decide(question, called_tools):
                response += chunk
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': chunk,
                }
            tools = self.extract_tools(response)
            if not tools:
                break
            results = await self.call_tool(tools)

            called_tools += [
                {
                    'tool': tool['name'],
                    'arguments': tool['arguments'],
                    'isError': result.isError,
                    'result': result.content[0].text,
                }
                for tool, result in zip(tools, results, strict=True)
            ]
            called_tools_history = called_tools_history_template.render(
                called_tools=called_tools, question=question
            )
            yield {
                'is_task_complete': False,
                'require_user_input': False,
                'content': called_tools_history,
            }

        yield {
            'is_task_complete': True,
            'require_user_input': False,
            'content': 'Task completed',
        }


if __name__ == '__main__':
    agent = Agent(
        token_stream_callback=lambda token: print(token, end='', flush=True),
        mcp_url='https://gitmcp.io/google/A2A',
    )

    async def main():
        """Main function."""
        async for chunk in agent.stream('What is A2A Protocol?'):
            print(chunk)

    asyncio.run(main())
