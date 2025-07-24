from __future__ import annotations
import json
import logging

from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING, Callable

import httpx

from httpx_sse import SSEError, aconnect_sse
from pydantic import ValidationError

from a2a.utils import Transports

from a2a.client.client import Client, ClientConfig, Consumer
from a2a.client.jsonrpc_client import NewJsonRpcClient
from a2a.client.grpc_client import NewGrpcClient
from a2a.client.rest_client import NewRestfulClient
from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    Message,
    Task,
    TaskIdParams,
    TaskQueryParams,
    GetTaskPushNotificationConfigParams,
    TaskPushNotificationConfig,
)

logger = logging.getLogger(__name__)

ClientProducer = Callable[
    [
        AgentCard | str,
        ClientConfig,
        list[Consumer],
        list[ClientCallInterceptor]
    ],
    Client
]

class ClientFactory:

    def __init__(
        self,
        config: ClientConfig,
        consumers: list[Consumer],
    ):
        self._config = config
        self._consumers = consumers
        self._registry: dict[str, ClientProducer] = {}
        if Transports.JSONRPC in self._config.supported_transports:
            self._registry[Transports.JSONRPC] = NewJsonRpcClient
        if Transports.RESTful in self._config.supported_transports:
            self._registry[Transports.RESTful] = NewRestfulClient
        if Transports.GRPC in self._config.supported_transports:
            self._registry[Transports.GRPC] = NewGrpcClient

    def register(self, label: str, generator: ClientProducer):
        self._registry[label] = generator

    def create(
        self,
        card: AgentCard,
        consumers: list[Consumer] | None = None,
        interceptors: list[ClientCallInterceptor] | None = None,
    ) -> Client:
        # Determine preferential transport
        server_set = [card.preferredTransport or 'JSONRPC']
        if card.additionalInterfaces:
            server_set.extend(
                [x.transport for x in card.additionalInterfaces]
            )
        client_set = self._config.supported_transports or ['JSONRPC']
        transport = None
        if self._config.use_client_preference:
            for x in client_set:
                if x in server_set:
                    transport = x
                    break
        else:
            for x in server_set:
                if x in client_set:
                    transport = x
                    break
        if not transport:
            raise Exception('no compatible transports found.')
        if transport not in self._registry:
            raise Exception(f'no client available for {transport}')
        all_consumers = self._consumers
        if consumers:
            all_consumers.extend(consumers)
        return self._registry[transport](
            card, self._config, all_consumers, interceptors
        )

def minimal_agent_card(url: str, transports: list[str] = []) -> AgentCard:
    """Generates a minimal card to simplify bootstrapping client creation."""
    return AgentCard(
        url=url,
        preferredTransport=transports[0] if transports else None,
        additionalInterfaces=transports[1:] if len(transports) > 1 else [],
        supportsAuthenticatedExtendedCard=True,
        capabilities=AgentCapabilities(),
        defaultInputModes=[],
        defaultOutputModes=[],
        description='',
        skills=[],
        version='',
        name='',
    )
