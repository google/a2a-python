import logging
import os
import sys

import click
import uvicorn

from adk_agent_executor import ADKBraveSearchAgentExecutor
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill


load_dotenv()

logging.basicConfig()


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10009)
def main(host: str, port: int):
    # Ensure BRAVE_API_KEY is set for the Brave Search MCP server.
    if not os.getenv('BRAVE_API_KEY'):
        print(
            'BRAVE_API_KEY environment variable not set. This agent requires it to function.'
        )
        sys.exit(1)

    # Define the capabilities and skills of this Brave Search Agent.
    skill = AgentSkill(
        id='brave_search',
        name='Brave Search',
        description='Performs a Brave Search based on a query.',
        tags=['search', 'information retrieval', 'mcp', 'brave'],
        examples=[
            'Latest news about climate change',
            'What is the capital of Canada?',
        ],
    )

    agent_executor = ADKBraveSearchAgentExecutor()
    agent_card = AgentCard(
        name='ADK MCP Brave Search Agent',
        description='I can help you find information using Brave Search via MCP.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )
    app = A2AStarletteApplication(agent_card, request_handler)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
