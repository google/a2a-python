"""Authenticated user information."""

from abc import ABC, abstractmethod


class User(ABC):
    """A representation of an authenticated user."""

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Returns whether the current user is authenticated."""

    @property
    @abstractmethod
    def user_name(self) -> str:
        """Returns the user name of the current user."""


class UnauthenticatedUser(User):
    """A representation that no user has been authenticated in the request."""

    @property
    def is_authenticated(self) -> bool:
        """Returns whether the current user is authenticated."""
        return False

    @property
    def user_name(self) -> str:
        """Returns the user name of the current user."""
        return ''
