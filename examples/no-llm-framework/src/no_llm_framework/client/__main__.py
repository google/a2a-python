import asyncio
from typing import Literal


import asyncclick as click
import colorama
from no_llm_framework.client.agent import Agent


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=9999)
@click.option('--mode', 'mode', default='streaming')
@click.option('--question', 'question', required=True)
async def a_main(
    host: str,
    port: int,
    mode: Literal['completion', 'streaming'],
    question: str,
):
    """Main function to run the A2A Repo Agent client.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
        mode (Literal['completion', 'streaming']): The mode to run the server on.
        question (str): The question to ask the Agent.
    """  # noqa: E501
    agent = Agent(
        mode='stream',
        token_stream_callback=None,
        agent_urls=[f'http://{host}:{port}/'],
    )
    async for chunk in agent.stream(question):
        if chunk.startswith('<Agent name="'):
            print(colorama.Fore.CYAN + chunk, end='', flush=True)
        elif chunk.startswith('</Agent>'):
            print(colorama.Fore.RESET + chunk, end='', flush=True)
        else:
            print(chunk, end='', flush=True)


def main() -> None:
    """Main function to run the A2A Repo Agent client."""
    asyncio.run(a_main())


if __name__ == '__main__':
    main()
