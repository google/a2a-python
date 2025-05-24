import logging
from typing import Any

from fastapi import FastAPI, Request

from a2a.server.apps.jsonrpc import JSONRPCApplication, CallContextBuilder
from a2a.server.request_handlers.jsonrpc_handler import RequestHandler
from a2a.types import AgentCard

logger = logging.getLogger(__name__)


class A2AFastAPIApplication(JSONRPCApplication):
    """A FastAPI application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE)."""

    def __init__(self, agent_card: AgentCard, http_handler: RequestHandler):
        """Initializes the A2A FastAPI application.

        Args:
            agent_card: The AgentCard describing the agent's capabilities.
            http_handler: The handler instance responsible for processing A2A requests via http.
        """
        super().__init__(agent_card, http_handler)

    def build(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        **kwargs: Any,
    ) -> FastAPI:
        """Builds and returns the FastAPI application instance.

        Args:
            agent_card_url: The URL for the agent card endpoint.
            rpc_url: The URL for the A2A JSON-RPC endpoint
            **kwargs: Additional keyword arguments to pass to the FastAPI constructor.

        Returns:
            A configured FastAPI application instance.
        """
        app = FastAPI(**kwargs)

        @app.post(rpc_url)
        async def handle_a2a_request(request: Request):
            return await self._handle_requests(request)

        @app.get(agent_card_url)
        async def get_agent_card(request: Request):
            return await self._handle_get_agent_card(request)

        return app
