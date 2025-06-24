import logging

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response
else:
    try:
        from fastapi import FastAPI, Request, Response
    except ImportError:
        FastAPI = Any
        Request = Any
        Response = Any

from a2a.server.apps.jsonrpc.jsonrpc_app import (
    CallContextBuilder,
    JSONRPCApplication,
)
from a2a.server.request_handlers.jsonrpc_handler import RequestHandler
from a2a.types import AgentCard


logger = logging.getLogger(__name__)


class A2AFastAPIApplication(JSONRPCApplication):
    """A FastAPI application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE).
    """

    def __init__(
        self,
        agent_card: AgentCard,
        http_handler: RequestHandler,
        extended_agent_card: AgentCard | None = None,
        context_builder: CallContextBuilder | None = None,
    ):
        """Initializes the A2AFastAPIApplication.

        Args:
            agent_card: The AgentCard describing the agent's capabilities.
            http_handler: The handler instance responsible for processing A2A
              requests via http.
            extended_agent_card: An optional, distinct AgentCard to be served
              at the authenticated extended card endpoint.
            context_builder: The CallContextBuilder used to construct the
              ServerCallContext passed to the http_handler. If None, no
              ServerCallContext is passed.
        """
        super().__init__(
            agent_card=agent_card,
            http_handler=http_handler,
            extended_agent_card=extended_agent_card,
            context_builder=context_builder,
        )

    def add_routes_to_app(
        self,
        app: FastAPI,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        extended_agent_card_url: str = '/agent/authenticatedExtendedCard',
    ) -> None:
        """Adds the routes to the FastAPI application.

        Args:
            app: The FastAPI application to add the routes to.
            agent_card_url: The URL for the agent card endpoint.
            rpc_url: The URL for the A2A JSON-RPC endpoint.
            extended_agent_card_url: The URL for the authenticated extended agent card endpoint.
        """

        @app.post(rpc_url)
        async def handle_a2a_request(request: Request) -> Response:
            return await self._handle_requests(request)

        @app.get(agent_card_url)
        async def get_agent_card(request: Request) -> Response:
            return await self._handle_get_agent_card(request)

        if self.agent_card.supportsAuthenticatedExtendedCard:

            @app.get(extended_agent_card_url)
            async def get_extended_agent_card(request: Request) -> Response:
                return await self._handle_get_authenticated_extended_agent_card(
                    request
                )

    def build(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        extended_agent_card_url: str = '/agent/authenticatedExtendedCard',
        **kwargs: Any,
    ) -> FastAPI:
        """Builds and returns the FastAPI application instance.

        Args:
            agent_card_url: The URL for the agent card endpoint.
            rpc_url: The URL for the A2A JSON-RPC endpoint.
            extended_agent_card_url: The URL for the authenticated extended agent card endpoint.
            **kwargs: Additional keyword arguments to pass to the FastAPI constructor.

        Returns:
            A configured FastAPI application instance.
        """
        app = FastAPI(**kwargs)

        self.add_routes_to_app(
            app, agent_card_url, rpc_url, extended_agent_card_url
        )

        return app
