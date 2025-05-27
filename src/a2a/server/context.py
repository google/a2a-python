"""Defines the ServerCallContext class."""

import collections.abc
import typing

from a2a.auth.user import UnauthenticatedUser, User


State = collections.abc.MutableMapping[str, typing.Any]


class ServerCallContext:
    """A context passed when calling a server method.

    This class allows storing arbitrary user data in the state attribute.
    """

    def __init__(self, state: State | None = None, user: User | None = None):
        self._state = state or {}
        self._user = user or UnauthenticatedUser()

    @property
    def user(self) -> User:
        """Get the user associated with this context, or UnauthenticatedUser."""
        return self._user

    @property
    def state(self) -> State:
        """Get the user-provided state."""
        return self._state
