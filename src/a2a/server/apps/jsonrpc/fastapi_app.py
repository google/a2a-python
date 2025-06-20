import logging

from typing import Any

from fastapi import FastAPI

from a2a.server.apps.jsonrpc.jsonrpc_app import (
    JSONRPCApplication,
)


logger = logging.getLogger(__name__)


class A2AFastAPIApplication(JSONRPCApplication):
    """A FastAPI application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE).
    """

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
        route_definitions = self._get_route_definitions(
            agent_card_url, rpc_url, extended_agent_card_url
        )

        for route_def in route_definitions:
            app.add_api_route(**route_def)

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
