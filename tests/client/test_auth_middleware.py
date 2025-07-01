from typing import Any

import httpx
import pytest
import respx

from a2a.client import A2AClient, ClientCallContext, ClientCallInterceptor
from a2a.client.auth import AuthInterceptor, InMemoryContextCredentialStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    APIKeySecurityScheme,
    AuthorizationCodeOAuthFlow,
    In,
    Message,
    MessageSendParams,
    OAuth2SecurityScheme,
    OAuthFlows,
    OpenIdConnectSecurityScheme,
    Role,
    SecurityScheme,
    SendMessageRequest,
)


# A simple mock interceptor for testing basic middleware functionality
class HeaderInterceptor(ClientCallInterceptor):
    def __init__(self, header_name: str, header_value: str):
        self.header_name = header_name
        self.header_value = header_value

    async def intercept(
        self,
        method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: AgentCard | None,
        context: ClientCallContext | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        headers = http_kwargs.get('headers', {})
        headers[self.header_name] = self.header_value
        http_kwargs['headers'] = headers
        return request_payload, http_kwargs


@pytest.mark.asyncio
@respx.mock
async def test_client_with_simple_interceptor():
    """
    Tests that a basic interceptor is called and successfully
    modifies the outgoing request headers.
    """
    # Arrange
    test_url = 'http://fake-agent.com/rpc'
    header_interceptor = HeaderInterceptor('X-Test-Header', 'Test-Value-123')
    async with httpx.AsyncClient() as http_client:
        client = A2AClient(
            httpx_client=http_client,
            url=test_url,
            interceptors=[header_interceptor],
        )

        # Mock the HTTP response with a minimal valid success response
        minimal_success_response = {
            'jsonrpc': '2.0',
            'id': '1',
            'result': {
                'kind': 'message',
                'messageId': 'response-msg',
                'role': 'agent',
                'parts': [],
            },
        }
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=minimal_success_response)
        )

        # Act
        await client.send_message(
            request=SendMessageRequest(
                id='1',
                params=MessageSendParams(
                    message=Message(
                        messageId='msg1',
                        role=Role.user,
                        parts=[],
                    )
                ),
            )
        )

        # Assert
        assert len(respx.calls) == 1
        request = respx.calls.last.request
        assert 'x-test-header' in request.headers
        assert request.headers['x-test-header'] == 'Test-Value-123'


@pytest.mark.asyncio
async def test_in_memory_context_credential_store():
    """
    Tests the functionality of the InMemoryContextCredentialStore to ensure
    it correctly stores and retrieves credentials based on sessionId.
    """
    # Arrange
    store = InMemoryContextCredentialStore()
    session_id = 'test-session-123'
    scheme_name = 'test-scheme'
    credential = 'test-token'

    # Act
    await store.set_credentials(session_id, scheme_name, credential)

    # Assert: Successful retrieval
    context = ClientCallContext(state={'sessionId': session_id})
    retrieved_credential = await store.get_credentials(scheme_name, context)
    assert retrieved_credential == credential

    # Assert: Retrieval with wrong session ID returns None
    wrong_context = ClientCallContext(state={'sessionId': 'wrong-session'})
    retrieved_credential_wrong = await store.get_credentials(
        scheme_name, wrong_context
    )
    assert retrieved_credential_wrong is None

    # Assert: Retrieval with no context returns None
    retrieved_credential_none = await store.get_credentials(scheme_name, None)
    assert retrieved_credential_none is None

    # Assert: Retrieval with context but no sessionId returns None
    empty_context = ClientCallContext(state={})
    retrieved_credential_empty = await store.get_credentials(
        scheme_name, empty_context
    )
    assert retrieved_credential_empty is None


@pytest.mark.asyncio
@respx.mock
async def test_auth_interceptor_with_api_key():
    """
    Tests the authentication flow with an API key in the header.
    """
    # Arrange
    test_url = 'http://apikey-agent.com/rpc'
    session_id = 'user-session-2'
    scheme_name = 'apiKeyAuth'
    api_key = 'secret-api-key'

    cred_store = InMemoryContextCredentialStore()
    await cred_store.set_credentials(session_id, scheme_name, api_key)

    auth_interceptor = AuthInterceptor(credential_service=cred_store)

    api_key_scheme_params = {
        'type': 'apiKey',
        'name': 'X-API-Key',
        'in': In.header,
    }

    agent_card = AgentCard(
        url=test_url,
        name='ApiKeyBot',
        description='A bot that requires an API Key',
        version='1.0',
        defaultInputModes=[],
        defaultOutputModes=[],
        skills=[],
        capabilities=AgentCapabilities(),
        security=[{scheme_name: []}],
        securitySchemes={
            scheme_name: SecurityScheme(
                root=APIKeySecurityScheme(**api_key_scheme_params)
            )
        },
    )

    async with httpx.AsyncClient() as http_client:
        client = A2AClient(
            httpx_client=http_client,
            agent_card=agent_card,
            interceptors=[auth_interceptor],
        )

        minimal_success_response = {
            'jsonrpc': '2.0',
            'id': '1',
            'result': {
                'kind': 'message',
                'messageId': 'response-msg',
                'role': 'agent',
                'parts': [],
            },
        }
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=minimal_success_response)
        )

        # Act
        context = ClientCallContext(state={'sessionId': session_id})
        await client.send_message(
            request=SendMessageRequest(
                id='1',
                params=MessageSendParams(
                    message=Message(
                        messageId='msg1',
                        role=Role.user,
                        parts=[],
                    )
                ),
            ),
            context=context,
        )

        # Assert
        assert len(respx.calls) == 1
        request = respx.calls.last.request
        assert 'x-api-key' in request.headers
        assert request.headers['x-api-key'] == api_key


@pytest.mark.asyncio
@respx.mock
async def test_auth_interceptor_with_oauth2_scheme():
    """
    Tests the AuthInterceptor with an OAuth2 security scheme defined in AgentCard.
    Ensures it correctly sets the Authorization: Bearer <token> header.
    """
    test_url = 'http://oauth-agent.com/rpc'
    session_id = 'user-session-oauth'
    scheme_name = 'myOAuthScheme'
    access_token = 'secret-oauth-access-token'

    cred_store = InMemoryContextCredentialStore()
    await cred_store.set_credentials(session_id, scheme_name, access_token)

    auth_interceptor = AuthInterceptor(credential_service=cred_store)

    oauth_flows = OAuthFlows(
        authorizationCode=AuthorizationCodeOAuthFlow(
            authorizationUrl='http://provider.com/auth',
            tokenUrl='http://provider.com/token',
            scopes={'read': 'Read scope'},
        )
    )

    agent_card = AgentCard(
        url=test_url,
        name='OAuthBot',
        description='A bot that uses OAuth2',
        version='1.0',
        defaultInputModes=[],
        defaultOutputModes=[],
        skills=[],
        capabilities=AgentCapabilities(),
        security=[{scheme_name: ['read']}],
        securitySchemes={
            scheme_name: SecurityScheme(
                root=OAuth2SecurityScheme(type='oauth2', flows=oauth_flows)
            )
        },
    )

    async with httpx.AsyncClient() as http_client:
        client = A2AClient(
            httpx_client=http_client,
            agent_card=agent_card,
            interceptors=[auth_interceptor],
        )

        minimal_success_response = {
            'jsonrpc': '2.0',
            'id': 'oauth_test_1',
            'result': {
                'kind': 'message',
                'messageId': 'response-msg-oauth',
                'role': 'agent',
                'parts': [],
            },
        }
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=minimal_success_response)
        )

        # Act
        context = ClientCallContext(state={'sessionId': session_id})
        await client.send_message(
            request=SendMessageRequest(
                id='oauth_test_1',
                params=MessageSendParams(
                    message=Message(
                        messageId='msg-oauth',
                        role=Role.user,
                        parts=[],
                    )
                ),
            ),
            context=context,
        )

        # Assert
        assert len(respx.calls) == 1
        request_sent = respx.calls.last.request
        assert 'Authorization' in request_sent.headers
        assert request_sent.headers['Authorization'] == f'Bearer {access_token}'


@pytest.mark.asyncio
@respx.mock
async def test_auth_interceptor_with_oidc_scheme():
    """
    Tests the AuthInterceptor with an OpenIdConnectSecurityScheme.
    Ensures it correctly sets the Authorization: Bearer <token> header.
    """
    # Arrange
    test_url = 'http://oidc-agent.com/rpc'
    session_id = 'user-session-oidc'
    scheme_name = 'myOidcScheme'
    id_token = 'secret-oidc-id-token'

    cred_store = InMemoryContextCredentialStore()
    await cred_store.set_credentials(session_id, scheme_name, id_token)

    auth_interceptor = AuthInterceptor(credential_service=cred_store)

    agent_card = AgentCard(
        url=test_url,
        name='OidcBot',
        description='A bot that uses OpenID Connect',
        version='1.0',
        defaultInputModes=[],
        defaultOutputModes=[],
        skills=[],
        capabilities=AgentCapabilities(),
        security=[{scheme_name: []}],
        securitySchemes={
            scheme_name: SecurityScheme(
                root=OpenIdConnectSecurityScheme(
                    type='openIdConnect',
                    openIdConnectUrl='http://provider.com/.well-known/openid-configuration',
                )
            )
        },
    )

    async with httpx.AsyncClient() as http_client:
        client = A2AClient(
            httpx_client=http_client,
            agent_card=agent_card,
            interceptors=[auth_interceptor],
        )

        minimal_success_response = {
            'jsonrpc': '2.0',
            'id': 'oidc_test_1',
            'result': {
                'kind': 'message',
                'messageId': 'response-msg-oidc',
                'role': 'agent',
                'parts': [],
            },
        }
        respx.post(test_url).mock(
            return_value=httpx.Response(200, json=minimal_success_response)
        )

        # Act
        context = ClientCallContext(state={'sessionId': session_id})
        await client.send_message(
            request=SendMessageRequest(
                id='oidc_test_1',
                params=MessageSendParams(
                    message=Message(
                        messageId='msg-oidc',
                        role=Role.user,
                        parts=[],
                    )
                ),
            ),
            context=context,
        )

        # Assert
        assert len(respx.calls) == 1
        request_sent = respx.calls.last.request
        assert 'Authorization' in request_sent.headers
        assert request_sent.headers['Authorization'] == f'Bearer {id_token}'
