import logging

from typing import Any

from starlette.applications import Starlette
from starlette.routing import Route

from a2a.server.apps.jsonrpc.jsonrpc_app import (
    JSONRPCApplication,
)


logger = logging.getLogger(__name__)


class A2AStarletteApplication(JSONRPCApplication):
    """A Starlette application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE).
    """

    def routes(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        extended_agent_card_url: str = '/agent/authenticatedExtendedCard',
    ) -> list[Route]:
        """Returns the Starlette Routes for handling A2A requests.

        Args:
            agent_card_url: The URL path for the agent card endpoint.
            rpc_url: The URL path for the A2A JSON-RPC endpoint (POST requests).
            extended_agent_card_url: The URL for the authenticated extended agent card endpoint.

        Returns:
            A list of Starlette Route objects.
        """
        route_definitions = self._get_route_definitions(
            agent_card_url, rpc_url, extended_agent_card_url
        )
        return [Route(**route_def) for route_def in route_definitions]

    def add_routes_to_app(
        self,
        app: Starlette,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        extended_agent_card_url: str = '/agent/authenticatedExtendedCard',
    ) -> None:
        """Adds the routes to the Starlette application.

        Args:
            app: The Starlette application to add the routes to.
            agent_card_url: The URL path for the agent card endpoint.
            rpc_url: The URL path for the A2A JSON-RPC endpoint (POST requests).
            extended_agent_card_url: The URL for the authenticated extended agent card endpoint.
        """
        app_routes = self.routes(
            agent_card_url=agent_card_url,
            rpc_url=rpc_url,
            extended_agent_card_url=extended_agent_card_url,
        )
        app.routes.extend(app_routes)

    def build(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        extended_agent_card_url: str = '/agent/authenticatedExtendedCard',
        **kwargs: Any,
    ) -> Starlette:
        """Builds and returns the Starlette application instance.

        Args:
            agent_card_url: The URL path for the agent card endpoint.
            rpc_url: The URL path for the A2A JSON-RPC endpoint (POST requests).
            extended_agent_card_url: The URL for the authenticated extended agent card endpoint.
            **kwargs: Additional keyword arguments to pass to the Starlette constructor.

        Returns:
            A configured Starlette application instance.
        """
        app = Starlette(**kwargs)

        self.add_routes_to_app(
            app, agent_card_url, rpc_url, extended_agent_card_url
        )

        return app
