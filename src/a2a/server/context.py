"""Defines the ServerCallContext class."""

import collections.abc
import typing


State = collections.abc.MutableMapping[str, typing.Any]


class ServerCallContext:
    """A context passed when calling a server method.

    This class allows storing arbitrary user data in the state attribute.
    """

    def __init__(self, state: State | None = None):
        if state is None:
            state = {}
        self._state = state

    @property
    def state(self) -> State:
        """Get the user-provided state."""
        return self._state
