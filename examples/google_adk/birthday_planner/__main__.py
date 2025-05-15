import asyncio
import functools
import logging
import os

import click
import uvicorn

from adk_agent_executor import ADKAgentExecutor
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)


load_dotenv()

logging.basicConfig()


def make_sync(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10008)
@click.option(
    '--calendar-agent', 'calendar_agent', default='http://localhost:10007'
)
def main(host: str, port: int, calendar_agent: str):
    # Verify an API key is set. Not required if using Vertex AI APIs, since those can use gcloud credentials.
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI') != 'TRUE' and not os.getenv(
        'GOOGLE_API_KEY'
    ):
        raise ValueError(
            'GOOGLE_API_KEY environment variable not set and GOOGLE_GENAI_USE_VERTEXAI is not TRUE.'
        )

    skill = AgentSkill(
        id='plan_parties',
        name='Plan a Birthday Party',
        description='Plan a birthday party, including times, activities, and themes.',
        tags=['event-planning'],
        examples=[
            'My son is turning 3 on August 2nd! What should I do for his party?',
            'Can you add the details to my calendar?',
        ],
    )

    agent_executor = ADKAgentExecutor(calendar_agent)
    agent_card = AgentCard(
        name='Birthday Planner',
        description='I can help you plan fun birthday parties.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        authentication=AgentAuthentication(schemes=['public']),
    )
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )
    app = A2AStarletteApplication(agent_card, request_handler)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
