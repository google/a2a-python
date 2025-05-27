import asyncio
import logging
import os

import click
import uvicorn

from foundry_agent_executor import create_foundry_agent_executor
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10007)
def main(host: str, port: int):
    """
    Run the AI Foundry A2A demo server.
    """
    # Verify required environment variables
    required_env_vars = [
        'AZURE_AI_FOUNDRY_PROJECT_ENDPOINT',
        'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Define agent skills
    skills = [
        AgentSkill(
            id='check_availability',
            name='Check Calendar Availability',
            description="Check if a user is available at a specific time using their calendar",
            tags=['calendar', 'scheduling'],
            examples=[
                'Am I free from 10am to 11am tomorrow?',
                'Check my availability for next Tuesday afternoon',
                'Do I have any conflicts on Friday morning?'
            ],
        ),
        AgentSkill(
            id='get_upcoming_events',
            name='Get Upcoming Events',
            description="Retrieve upcoming calendar events for the user",
            tags=['calendar', 'events'],
            examples=[
                'What meetings do I have today?',
                'Show me my schedule for this week',
                'What\'s coming up in the next few hours?'
            ],
        ),
        AgentSkill(
            id='calendar_management',
            name='Calendar Management',
            description="General calendar management and scheduling assistance",
            tags=['calendar', 'productivity'],
            examples=[
                'Help me manage my calendar',
                'When is the best time for a meeting?',
                'Optimize my schedule for tomorrow'
            ],
        )
    ]

    # Create agent card
    agent_card = AgentCard(
        name='AI Foundry Calendar Agent',
        description="An intelligent calendar management agent powered by Azure AI Foundry. "
                   "I can help you check availability, manage events, and optimize your schedule.",
        url=f'http://{host}:{port}/',
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=skills,
    )

    # Create agent executor
    agent_executor = create_foundry_agent_executor(agent_card)

    # Create request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, 
        task_store=InMemoryTaskStore()
    )

    # Create A2A application
    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, 
        http_handler=request_handler
    )
    
    # Get routes
    routes = a2a_app.routes()
    
    # Add health check endpoint
    async def health_check(request: Request) -> PlainTextResponse:
        return PlainTextResponse('AI Foundry Calendar Agent is running!')
    
    routes.append(
        Route(
            path='/health',
            methods=['GET'],
            endpoint=health_check
        )
    )

    # Create Starlette app
    app = Starlette(routes=routes)
    
    # Log startup information
    logger.info(f"Starting AI Foundry Calendar Agent on {host}:{port}")
    logger.info(f"Agent card: {agent_card.name}")
    logger.info(f"Skills: {[skill.name for skill in skills]}")
    logger.info(f"Health check available at: http://{host}:{port}/health")
    
    # Run the server
    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()
