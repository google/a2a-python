import logging
import os

import click
import uvicorn


# Use absolute import for the executor
from adk_agent_executor import ADKSpanishTranslationAgentExecutor
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
@click.option('--port', 'port', default=10010)
def main(host: str, port: int):
    # Ensure OPENAI_API_KEY is set for the OpenAI model used via LiteLLM.
    if not os.getenv('OPENAI_API_KEY'):
        logger.error(
            'OPENAI_API_KEY environment variable not set. This agent may not function correctly.'
        )

    # Define the capabilities and skills of this Spanish Translation Agent.
    skill = AgentSkill(
        id='translate_to_spanish',
        name='Translate to Spanish',
        description='Translates provided text into Spanish.',
        tags=['translation', 'spanish', 'language'],
        examples=[
            'Translate "Hello, world!" to Spanish',
            'Could you translate "Good morning" into Spanish?',
        ],
    )

    agent_executor = ADKSpanishTranslationAgentExecutor()
    agent_card = AgentCard(
        name='ADK Spanish Translation Agent',
        description='I can translate text into Spanish.',
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
        f'Starting Spanish Translation Agent server on http://{host}:{port}'
    )
    logger.info(
        "This agent is identified by 'spanish_translator' for delegation."
    )
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
