import logging

from typing import Any

from starlette.applications import Starlette
from starlette.routing import Route

from a2a.server.apps import DefaultA2AApplication
from a2a.server.request_handlers.jsonrpc_handler import RequestHandler
from a2a.types import AgentCard


logger = logging.getLogger(__name__)


class A2AStarletteApplication(DefaultA2AApplication):
    """A Starlette application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE).
    """

    def __init__(self, agent_card: AgentCard, http_handler: RequestHandler):
        """Initializes the A2AApplication.

        Args:
            agent_card: The AgentCard describing the agent's capabilities.
            http_handler: The handler instance responsible for processing A2A
              requests via http.
        """
        super().__init__(agent_card, http_handler)

    def routes(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
    ) -> list[Route]:
        """Returns the Starlette Routes for handling A2A requests.

        Args:
            agent_card_url: The URL for the agent card endpoint.
            rpc_url: The URL for the A2A JSON-RPC endpoint

        Returns:
            The Starlette Routes serving A2A requests.
        """
        return [
            Route(
                rpc_url,
                self._handle_requests,
                methods=['POST'],
                name='a2a_handler',
            ),
            Route(
                agent_card_url,
                self._handle_get_agent_card,
                methods=['GET'],
                name='agent_card',
            ),
        ]
    
    def build(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        **kwargs: Any,
    ) -> Starlette:
        """Builds and returns the Starlette application instance.

        Args:
            agent_card_url: The URL for the agent card endpoint.
            rpc_url: The URL for the A2A JSON-RPC endpoint
            **kwargs: Additional keyword arguments to pass to the Starlette
              constructor.

        Returns:
            A configured Starlette application instance.
        """
        routes = self.routes(agent_card_url, rpc_url)
        if 'routes' in kwargs:
            kwargs['routes'] += routes
        else:
            kwargs['routes'] = routes

        return Starlette(**kwargs)
