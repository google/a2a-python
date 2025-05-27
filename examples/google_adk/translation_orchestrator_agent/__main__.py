import logging
import os

import click
import uvicorn

from adk_agent_executor import ADKTranslationOrchestratorAgentExecutor
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
@click.option('--port', 'port', default=10012)
def main(host: str, port: int):
    # Ensure GOOGLE_API_KEY is set for the orchestrator's Gemini model.
    if not os.getenv('GOOGLE_API_KEY'):
        logger.error(
            'GOOGLE_API_KEY environment variable not set for orchestrator. This agent may not function correctly.'
        )

    # Define the skills exposed by the orchestrator agent.
    skill_spanish = AgentSkill(
        id='translate_text_to_spanish',
        name='Translate to Spanish',
        description='Translates provided text into Spanish by delegating to a specialized agent.',
        tags=['translation', 'spanish', 'orchestration'],
        examples=[
            'Translate "Hello, world!" to Spanish',
            'Can you say "Good morning" in Spanish?',
        ],
    )

    skill_french = AgentSkill(
        id='translate_text_to_french',
        name='Translate to French',
        description='Translates provided text into French by delegating to a specialized agent.',
        tags=['translation', 'french', 'orchestration'],
        examples=[
            'Translate "Hello, world!" to French',
            'Can you say "Good morning" in French?',
        ],
    )

    skill_search_and_translate = AgentSkill(
        id='search_and_translate_news',
        name='Search and Translate News',
        description='Searches for news on a given topic and translates the results to Spanish or French.',
        tags=['search', 'news', 'translation', 'orchestration'],
        examples=[
            'What is the latest AI news in French?',
            'Find recent developments in quantum computing and translate to Spanish.',
        ],
    )

    agent_executor = ADKTranslationOrchestratorAgentExecutor()
    agent_card = AgentCard(
        name='ADK Translation Orchestrator Agent',
        description='I can orchestrate translations to Spanish or French, and search for news and translate it.',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill_spanish, skill_french, skill_search_and_translate],
    )
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )
    app = A2AStarletteApplication(agent_card, request_handler)

    logger.info(
        f'Starting Translation Orchestrator Agent server on http://{host}:{port}'
    )
    logger.info(
        'This agent identifies itself to clients with the ID: translation_orchestrator.'
    )
    logger.info('This agent will delegate to:')
    logger.info(
        '  - Spanish Translator (expected ID: spanish_translator, e.g., on port 10010)'
    )
    logger.info(
        '  - French Translator (expected ID: french_translator, e.g., on port 10011)'
    )
    logger.info(
        '  - Brave Search Agent (expected ID: mcp_brave_search_agent_adk, e.g., on port 10009)'
    )

    uvicorn.run(app.build(), host=host, port=port)


if __name__ == '__main__':
    main()
