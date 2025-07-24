"""Client-side components for interacting with an A2A agent."""

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
