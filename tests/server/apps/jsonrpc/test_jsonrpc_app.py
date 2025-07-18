from unittest.mock import MagicMock

import pytest


# Attempt to import StarletteBaseUser, fallback to MagicMock if not available
try:
    from starlette.authentication import BaseUser as StarletteBaseUser
except ImportError:
    StarletteBaseUser = MagicMock()  # type: ignore

from a2a.server.apps.jsonrpc.jsonrpc_app import (
    JSONRPCApplication,  # Still needed for JSONRPCApplication default constructor arg
    StarletteUserProxy,
)
from a2a.server.request_handlers.request_handler import (
    RequestHandler,  # For mock spec
)
from a2a.types import AgentCard  # For mock spec


# --- StarletteUserProxy Tests ---


class TestStarletteUserProxy:
    def test_starlette_user_proxy_is_authenticated_true(self):
        starlette_user_mock = MagicMock(spec=StarletteBaseUser)
        starlette_user_mock.is_authenticated = True
        proxy = StarletteUserProxy(starlette_user_mock)
        assert proxy.is_authenticated is True

    def test_starlette_user_proxy_is_authenticated_false(self):
        starlette_user_mock = MagicMock(spec=StarletteBaseUser)
        starlette_user_mock.is_authenticated = False
        proxy = StarletteUserProxy(starlette_user_mock)
        assert proxy.is_authenticated is False

    def test_starlette_user_proxy_user_name(self):
        starlette_user_mock = MagicMock(spec=StarletteBaseUser)
        starlette_user_mock.display_name = 'Test User DisplayName'
        proxy = StarletteUserProxy(starlette_user_mock)
        assert proxy.user_name == 'Test User DisplayName'

    def test_starlette_user_proxy_user_name_raises_attribute_error(self):
        """
        Tests that if the underlying starlette user object is missing the
        display_name attribute, the proxy currently raises an AttributeError.
        """
        starlette_user_mock = MagicMock(spec=StarletteBaseUser)
        # Ensure display_name is not present on the mock to trigger AttributeError
        del starlette_user_mock.display_name

        proxy = StarletteUserProxy(starlette_user_mock)
        with pytest.raises(AttributeError, match='display_name'):
            _ = proxy.user_name


# --- JSONRPCApplication Tests (Selected) ---


class TestJSONRPCApplicationSetup:  # Renamed to avoid conflict
    def test_jsonrpc_app_build_method_abstract_raises_typeerror(
        self,
    ):  # Renamed test
        mock_handler = MagicMock(spec=RequestHandler)
        # Mock agent_card with essential attributes accessed in JSONRPCApplication.__init__
        mock_agent_card = MagicMock(spec=AgentCard)
        # Ensure 'url' attribute exists on the mock_agent_card, as it's accessed in __init__
        mock_agent_card.url = 'http://mockurl.com'
        # Ensure 'supportsAuthenticatedExtendedCard' attribute exists
        mock_agent_card.supports_authenticated_extended_card = False

        # This will fail at definition time if an abstract method is not implemented
        with pytest.raises(
            TypeError,
            match="Can't instantiate abstract class IncompleteJSONRPCApp with abstract method build",
        ):

            class IncompleteJSONRPCApp(JSONRPCApplication):
                # Intentionally not implementing 'build'
                def some_other_method(self):
                    pass

            IncompleteJSONRPCApp(
                agent_card=mock_agent_card, http_handler=mock_handler
            )


if __name__ == '__main__':
    pytest.main([__file__])
