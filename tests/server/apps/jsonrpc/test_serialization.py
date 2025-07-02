from unittest import mock

import pytest

from pydantic import ValidationError
from starlette.testclient import TestClient

from a2a.server.apps import A2AFastAPIApplication, A2AStarletteApplication
from a2a.types import (
    APIKeySecurityScheme,
    AgentCapabilities,
    AgentCard,
    In,
    SecurityScheme,
    WellKnownUris,
)


@pytest.fixture
def agent_card_with_api_key():
    """Provides an AgentCard with an APIKeySecurityScheme for testing serialization."""
    # This data uses the alias 'in', which is correct for creating the model.
    api_key_scheme_data = {
        'type': 'apiKey',
        'name': 'X-API-KEY',
        'in': 'header',
    }
    api_key_scheme = APIKeySecurityScheme.model_validate(api_key_scheme_data)

    agent_card = AgentCard(
        name='APIKeyAgent',
        description='An agent that uses API Key auth.',
        url='http://example.com/apikey-agent',
        version='1.0.0',
        capabilities=AgentCapabilities(),
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        skills=[],
        securitySchemes={'api_key_auth': SecurityScheme(root=api_key_scheme)},
        security=[{'api_key_auth': []}],
    )
    return agent_card


def test_starlette_agent_card_with_api_key_scheme_alias(
    agent_card_with_api_key: AgentCard,
):
    """
    Tests that the A2AStarletteApplication endpoint correctly serializes aliased fields.

    This verifies the fix for `APIKeySecurityScheme.in_` being serialized as `in_` instead of `in`.
    """
    handler = mock.AsyncMock()
    app_instance = A2AStarletteApplication(agent_card_with_api_key, handler)
    client = TestClient(app_instance.build())

    response = client.get(WellKnownUris.AGENT_CARD_WELL_KNOWN_URI)
    assert response.status_code == 200
    response_data = response.json()

    security_scheme_json = response_data['securitySchemes']['api_key_auth']
    assert 'in' in security_scheme_json
    assert security_scheme_json['in'] == 'header'
    assert 'in_' not in security_scheme_json

    try:
        parsed_card = AgentCard.model_validate(response_data)
        parsed_scheme_wrapper = parsed_card.securitySchemes['api_key_auth']
        assert isinstance(parsed_scheme_wrapper.root, APIKeySecurityScheme)
        assert parsed_scheme_wrapper.root.in_ == In.header
    except ValidationError as e:
        pytest.fail(
            f"AgentCard.model_validate failed on the server's response: {e}"
        )


def test_fastapi_agent_card_with_api_key_scheme_alias(
    agent_card_with_api_key: AgentCard,
):
    """
    Tests that the A2AFastAPIApplication endpoint correctly serializes aliased fields.

    This verifies the fix for `APIKeySecurityScheme.in_` being serialized as `in_` instead of `in`.
    """
    handler = mock.AsyncMock()
    app_instance = A2AFastAPIApplication(agent_card_with_api_key, handler)
    client = TestClient(app_instance.build())

    response = client.get(WellKnownUris.AGENT_CARD_WELL_KNOWN_URI)
    assert response.status_code == 200
    response_data = response.json()

    security_scheme_json = response_data['securitySchemes']['api_key_auth']
    assert 'in' in security_scheme_json
    assert 'in_' not in security_scheme_json
    assert security_scheme_json['in'] == 'header'
