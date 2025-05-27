# 🐍 Python Standard Library Imports
import logging
import os  # For accessing environment variables
import sys  # For exiting the script

# 🔩 Third-party Library Imports
import click  # For creating command-line interfaces
import uvicorn  # ASGI server for running Starlette/FastAPI apps


# 🏠 Local Application/Library Specific Imports
from adk_agent_executor import (
    ADKSearchAgentExecutor,  # The agent executor we defined
)
from dotenv import (
    load_dotenv,  # For loading environment variables from a .env file
)

# 🚀 A2A SDK Imports
from a2a.server.apps import (
    A2AStarletteApplication,  # Base Starlette application for A2A servers
)
from a2a.server.request_handlers import (
    DefaultRequestHandler,  # Default request handler for A2A methods
)
from a2a.server.tasks import InMemoryTaskStore  # Simple in-memory task store
from a2a.types import AgentCapabilities, AgentCard, AgentSkill  # Core A2A types


# 🌍 Load environment variables from a .env file in the current directory
load_dotenv()

# 📝 Configure basic logging for the application
logging.basicConfig(
    level=logging.INFO
)  # Set to INFO for general operational messages
# For more detailed debugging from this script or A2A/ADK components,
# you might set this to logging.DEBUG, or configure specific loggers.


# 🚀 Define the main CLI command using Click
@click.command()
@click.option(
    '--host',
    'host',
    default='localhost',
    help='Hostname to bind the server to.',
)
@click.option(
    '--port',
    'port',
    default=10009,
    type=int,
    help='Port number to bind the server to.',
)
def main(host: str, port: int):
    """🚀 Main function to configure and run the A2A Search Agent server."""
    # 🔑 Check for GOOGLE_API_KEY environment variable
    # This is crucial for the Google Search tool used by the ADK agent.
    if not os.getenv('GOOGLE_API_KEY'):
        # 🚫 API Key is missing, print an error and exit.
        print(
            '🛑 ERROR: GOOGLE_API_KEY environment variable not set. This is required for the Google Search tool.'
        )
        print(
            'Please create a .env file in this directory with your GOOGLE_API_KEY or set it in your environment.'
        )
        print('Example .env content: GOOGLE_API_KEY="your_actual_api_key_here"')
        sys.exit(1)  # Exit with a non-zero status code to indicate an error.

    # 🛠️ Define the primary skill of this agent.
    # An AgentSkill describes a specific capability the agent offers.
    skill = AgentSkill(
        id='google_search',  # Unique identifier for this skill
        name='Google Search',  # Human-readable name for the skill
        description='Performs a Google Search based on location and query.',  # What the skill does
        tags=[
            'search',
            'information retrieval',
            'google',
        ],  # Keywords for discoverability
        examples=[  # Example phrases that might invoke this skill
            'Find coffee shops near 90210',
            'What is the capital of France in 75001?',
            'Search for recent AI news in California',
        ],
    )

    # 🤖 Instantiate the Agent Executor.
    # This is the core logic component that connects to the ADK agent.
    agent_executor = ADKSearchAgentExecutor()

    # 🃏 Create the Agent Card.
    # The AgentCard provides metadata about the agent, making it discoverable and understandable by clients.
    agent_card = AgentCard(
        name='ADK Google Search Agent 🔎',  # Human-readable name of the agent (added an icon!)
        description='I am an agent powered by Google ADK. I can perform Google searches for you based on a query and optional location.',  # Detailed description
        url=f'http://{host}:{port}/',  # The root URL where this agent is accessible
        version='1.0.0',  # Version of this agent
        defaultInputModes=[
            'text'
        ],  # Default ways the agent can receive input (e.g., 'text', 'speech')
        defaultOutputModes=[
            'text'
        ],  # Default ways the agent can produce output
        capabilities=AgentCapabilities(
            streaming=True  # Indicates if the agent supports streaming responses
            # Other capabilities like `tool_calling`, `function_calling` could be listed here.
        ),
        skills=[
            skill
        ],  # List of skills this agent possesses (we defined one above)
        # `icon_url`, `author`, `license` are other useful fields for an AgentCard.
    )

    # 🔄 Configure the Request Handler.
    # The request handler processes incoming JSON-RPC requests and routes them to the agent executor.
    # `InMemoryTaskStore` is used here, meaning task states are kept in memory and lost on restart.
    # For production, a persistent task store (e.g., Redis, database) would be preferable.
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,  # The executor that will handle the agent logic
        task_store=InMemoryTaskStore(),  # Store for tracking task progress
    )

    # 🌐 Create the A2A Starlette Application.
    # This wraps the agent card and request handler into an ASGI application (compatible with Uvicorn).
    app = A2AStarletteApplication(
        agent_card=agent_card,  # The agent's metadata card
        http_handler=request_handler,  # The handler for incoming requests
    )

    # ▶️ Run the Uvicorn server.
    # `app.build()` creates the actual Starlette application instance.
    # Uvicorn is an ASGI server that will host our A2A agent.
    print(f'🚀 Starting ADK Search Agent server on http://{host}:{port}')
    print(
        f'📄 Agent Card available at http://{host}:{port}/.well-known/agent.json'
    )
    print(f'📡 JSON-RPC endpoint at http://{host}:{port}/jsonrpc')
    uvicorn.run(app.build(), host=host, port=port, log_level='info')


# 🏁 Standard Python entry point guard
if __name__ == '__main__':
    # Execute the main function (which is our Click command)
    main()
