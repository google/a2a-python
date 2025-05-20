import os
import sys
from typing import Dict, Any, List
import asyncio
from contextlib import asynccontextmanager

import click
import uvicorn

from agent import AirbnbAgent
from agent_executor import AirbnbAgentExecutor
from dotenv import load_dotenv

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.server.tasks import InMemoryTaskStore
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv(override=True)

SERVER_CONFIGS = {
    "bnb": {
        "command": "npx",
        "args": ["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"],
        "transport": "stdio",
    },
}

app_context: Dict[str, Any] = {}


@asynccontextmanager
async def app_lifespan(context: Dict[str, Any]):
    """Manages the lifecycle of shared resources like the MCP client and tools."""
    print("Lifespan: Initializing MCP client and tools...")

    # This variable will hold the MultiServerMCPClient instance
    mcp_client_instance: MultiServerMCPClient | None = None

    try:
        # Following Option 1 from the error message for MultiServerMCPClient initialization:
        # 1. client = MultiServerMCPClient(...)
        mcp_client_instance = MultiServerMCPClient(SERVER_CONFIGS)
        mcp_tools = await mcp_client_instance.get_tools()
        context["mcp_tools"] = mcp_tools

        tool_count = len(mcp_tools) if mcp_tools else 0
        print(f"Lifespan: MCP Tools preloaded successfully ({tool_count} tools found).")
        yield  # Application runs here
    except Exception as e:
        print(f"Lifespan: Error during initialization: {e}", file=sys.stderr)
        # If an exception occurs, mcp_client_instance might exist and need cleanup.
        # The finally block below will handle this.
        raise
    finally:
        print("Lifespan: Shutting down MCP client...")
        if (
            mcp_client_instance
        ):  # Check if the MultiServerMCPClient instance was created
            # The original code called __aexit__ on the MultiServerMCPClient instance
            # (which was mcp_client_manager). We assume this is still the correct cleanup method.
            if hasattr(mcp_client_instance, "__aexit__"):
                try:
                    print(
                        f"Lifespan: Calling __aexit__ on {type(mcp_client_instance).__name__} instance..."
                    )
                    await mcp_client_instance.__aexit__(None, None, None)
                    print("Lifespan: MCP Client resources released via __aexit__.")
                except Exception as e:
                    print(
                        f"Lifespan: Error during MCP client __aexit__: {e}",
                        file=sys.stderr,
                    )
            else:
                # This would be unexpected if only the context manager usage changed.
                # Log an error as this could lead to resource leaks.
                print(
                    f"Lifespan: CRITICAL - {type(mcp_client_instance).__name__} instance does not have __aexit__ method for cleanup. Resource leak possible.",
                    file=sys.stderr,
                )
        else:
            # This case means MultiServerMCPClient() constructor likely failed or was not reached.
            print(
                "Lifespan: MCP Client instance was not created, no shutdown attempt via __aexit__."
            )

        # Clear the application context as in the original code.
        print("Lifespan: Clearing application context.")
        context.clear()


@click.command()
@click.option(
    "--host", "host", default="localhost", help="Hostname to bind the server to."
)
@click.option(
    "--port", "port", default=10002, type=int, help="Port to bind the server to."
)
@click.option("--log-level", "log_level", default="info", help="Uvicorn log level.")
def cli_main(host: str, port: int, log_level: str):
    """Command Line Interface to start the Airbnb Agent server."""
    if not os.getenv("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    async def run_server_async():
        async with app_lifespan(app_context):
            if not app_context.get("mcp_tools"):
                print(
                    "Warning: MCP tools were not loaded. Agent may not function correctly.",
                    file=sys.stderr,
                )
                # Depending on requirements, you could sys.exit(1) here

            # Initialize AirbnbAgentExecutor with preloaded tools
            airbnb_agent_executor = AirbnbAgentExecutor(
                mcp_tools=app_context.get("mcp_tools", [])
            )

            request_handler = DefaultRequestHandler(
                agent_executor=airbnb_agent_executor,
                task_store=InMemoryTaskStore(),
            )

            # Create the A2AServer instance
            a2a_server = A2AStarletteApplication(
                agent_card=get_agent_card(host, port), http_handler=request_handler
            )

            # Get the ASGI app from the A2AServer instance
            asgi_app = a2a_server.build()

            config = uvicorn.Config(
                app=asgi_app,
                host=host,
                port=port,
                log_level=log_level.lower(),
                lifespan="auto",
            )

            uvicorn_server = uvicorn.Server(config)

            print(
                f"Starting Uvicorn server at http://{host}:{port} with log-level {log_level}..."
            )
            try:
                await uvicorn_server.serve()
            except KeyboardInterrupt:
                print("Server shutdown requested (KeyboardInterrupt).")
            finally:
                print("Uvicorn server has stopped.")
                # The app_lifespan's finally block handles mcp_client shutdown

    try:
        asyncio.run(run_server_async())
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            print(
                "Critical Error: Attempted to nest asyncio.run(). This should have been prevented.",
                file=sys.stderr,
            )
        else:
            print(f"RuntimeError in cli_main: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred in cli_main: {e}", file=sys.stderr)
        sys.exit(1)


def get_agent_card(host: str, port: int):
    """Returns the Agent Card for the Currency Agent."""
    capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
    skill = AgentSkill(
        id="airbnb_search",
        name="Search airbnb accommodation",
        description="Helps with accommodation search using airbnb",
        tags=["airbnb accommodation"],
        examples=[
            "Please find a room in LA, CA, April 15, 2025, checkout date is april 18, 2 adults"
        ],
    )
    return AgentCard(
        name="Airbnb Agent",
        description="Helps with searching accommodation",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=AirbnbAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill],
    )


if __name__ == "__main__":
    cli_main()
