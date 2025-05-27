import logging
import os

import click
import uvicorn

from adk_agent_executor import ADKFrenchTranslationAgentExecutor
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill


load_dotenv()

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10011)
def main(host: str, port: int):
    # Ensure GOOGLE_API_KEY is set for the Gemini model used by this agent.
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error(
            'GOOGLE_API_KEY environment variable not set. This agent may not function correctly.'
        )

    # Define the capabilities and skills of this French Translation Agent.
    skill = AgentSkill(
        id='translate_to_french',
        name='Translate to French',
        description='Translates provided text into French.',
        tags=['translation', 'french', 'language'],
        examples=[
            'Translate "Hello, world!" to French',
            'Could you translate "Good morning" into French?',
        ],
    )

    agent_executor = ADKFrenchTranslationAgentExecutor()
    agent_card = AgentCard(
        name='ADK French Translation Agent',
        description='I can translate text into French.',
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

    logger.info(
        f'Starting French Translation Agent server on http://{host}:{port}'
    )
    logger.info(
        "This agent is identified by 'french_translator' for delegation."
    )
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
