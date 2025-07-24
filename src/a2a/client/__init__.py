"""Client-side components for interacting with an A2A agent."""

import logging

from a2a.client.auth import (
    AuthInterceptor,
    CredentialService,
    InMemoryContextCredentialStore,
)
from a2a.client.errors import (
    A2AClientError,
    A2AClientHTTPError,
    A2AClientJSONError,
    A2AClientTimeoutError,
)
from a2a.client.jsonrpc_client import (
    JsonRpcClient,
    JsonRpcTransportClient,
    NewJsonRpcClient,
)
from a2a.client.grpc_client import (
    GrpcTransportClient,
    GrpcClient,
    NewGrpcClient,
)
from a2a.client.rest_client import (
    RestTransportClient,
    RestClient,
    NewRestfulClient,
)
from a2a.client.helpers import create_text_message_object
from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.client.client import (
    A2ACardResolver,
    Client,
    ClientConfig,
    Consumer,
    ClientEvent,
)
from a2a.client.client_factory import (
    ClientFactory,
    ClientProducer,
    minimal_agent_card
)

# For backward compatability define this alias. This will be deprecated in
# a future release.
A2AClient = JsonRpcTransportClient
A2AGrpcClient = GrpcTransportClient

logger = logging.getLogger(__name__)

try:
    from a2a.client.grpc_client import A2AGrpcClient  # type: ignore
except ImportError as e:
    _original_error = e
    logger.debug(
        'A2AGrpcClient not loaded. This is expected if gRPC dependencies are not installed. Error: %s',
        _original_error,
    )

    class A2AGrpcClient:  # type: ignore
        """Placeholder for A2AGrpcClient when dependencies are not installed."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                'To use A2AGrpcClient, its dependencies must be installed. '
                'You can install them with \'pip install "a2a-sdk[grpc]"\''
            ) from _original_error


__all__ = [
    'A2ACardResolver',
    'A2AClientError',
    'A2AClientHTTPError',
    'A2AClientJSONError',
    'A2AClientTimeoutError',
    'AuthInterceptor',
    'ClientCallContext',
    'ClientCallInterceptor',
    'Consumer',
    'CredentialService',
    'InMemoryContextCredentialStore',
    'create_text_message_object',
    'A2AClient',  # for backward compatability
    'A2AGrpcClient', # for backward compatability
    'Client',
    'ClientEvent',
    'ClientFactory',
    'ClientConfig',
    'ClientProducer',
    'GrpcTransportClient',
    'GrpcClient',
    'NewGrpcClient',
    'JsonRpcClient',
    'JsonRpcTransportClient',
    'NewJsonRpcClient',
    'minimal_agent_card',
    'RestTransportClient',
    'RestClient',
    'NewRestfulClient',
]
