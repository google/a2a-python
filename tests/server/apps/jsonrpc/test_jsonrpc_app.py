from unittest.mock import MagicMock

import pytest


# Attempt to import StarletteBaseUser, fallback to MagicMock if not available
try:
    from starlette.authentication import BaseUser as StarletteBaseUser
except ImportError:
    StarletteBaseUser = MagicMock()  # type: ignore

from a2a.server.apps.jsonrpc.jsonrpc_app import (
    StarletteUserProxy,
)


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


if __name__ == '__main__':
    pytest.main([__file__])
