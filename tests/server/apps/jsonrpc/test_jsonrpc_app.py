from typing import Any
from unittest.mock import MagicMock

import pytest


# Attempt to import StarletteBaseUser, fallback to MagicMock if not available
try:
    from starlette.authentication import BaseUser as StarletteBaseUser
except ImportError:
    StarletteBaseUser = MagicMock()  # type: ignore

from a2a.server.apps.jsonrpc import jsonrpc_app
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
        mock_agent_card.supportsAuthenticatedExtendedCard = False

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


class TestJSONRPCApplicationOptionalDeps:
    # Running tests in this class requires optional dependencies starlette and
    # sse-starlette to be present in the test environment.

    @pytest.fixture(scope='class', autouse=True)
    def ensure_pkg_starlette_is_present(self):
        try:
            import starlette as _starlette
            import sse_starlette as _sse_starlette
        except ImportError:
            pytest.fail(
                f'Running tests in {self.__class__.__name__} requires'
                ' optional dependencies starlette and sse-starlette to be'
                ' present in the test environment. Run `uv sync --dev ...`'
                ' before running the test suite.'
            )

    @pytest.fixture(scope='class')
    def mock_app_params(self) -> dict:
        # Mock http_handler
        mock_handler = MagicMock(spec=RequestHandler)
        # Mock agent_card with essential attributes accessed in __init__
        mock_agent_card = MagicMock(spec=AgentCard)
        # Ensure 'url' attribute exists on the mock_agent_card, as it's accessed
        # in __init__
        mock_agent_card.url = 'http://example.com'
        # Ensure 'supportsAuthenticatedExtendedCard' attribute exists
        mock_agent_card.supportsAuthenticatedExtendedCard = False
        return dict(agent_card=mock_agent_card, http_handler=mock_handler)

    @pytest.fixture(scope='class')
    def mark_pkg_starlette_not_installed(self):
        pkg_starlette_installed_flag = jsonrpc_app._package_starlette_installed
        jsonrpc_app._package_starlette_installed = False
        yield
        jsonrpc_app._package_starlette_installed = pkg_starlette_installed_flag

    def test_create_jsonrpc_based_app_with_present_deps_succeeds(
        self, mock_app_params: dict
    ):
        class DummyJSONRPCApp(JSONRPCApplication):
            def build(
                self,
                agent_card_url='/.well-known/agent.json',
                rpc_url='/',
                **kwargs,
            ):
                return object()

        try:
            _app = DummyJSONRPCApp(**mock_app_params)
        except ImportError:
            pytest.fail(
                'With packages starlette and see-starlette present, creating a'
                ' JSONRPCApplication-based instance should not raise'
                ' ImportError'
            )

    def test_create_jsonrpc_based_app_with_missing_deps_raises_importerror(
        self, mock_app_params: dict, mark_pkg_starlette_not_installed: Any
    ):
        class DummyJSONRPCApp(JSONRPCApplication):
            def build(
                self,
                agent_card_url='/.well-known/agent.json',
                rpc_url='/',
                **kwargs,
            ):
                return object()

        with pytest.raises(
            ImportError,
            match=(
                'Packages `starlette` and `sse-starlette` are required to use'
                ' the `JSONRPCApplication`'
            ),
        ):
            _app = DummyJSONRPCApp(**mock_app_params)


if __name__ == '__main__':
    pytest.main([__file__])
