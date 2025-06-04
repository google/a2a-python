# a2a/client/auth/credentials.py

from abc import ABC, abstractmethod

from a2a.client.middleware import ClientCallContext


class CredentialService(ABC):
    """An abstract service for retrieving credentials."""

    @abstractmethod
    async def get_credentials(
        self,
        security_scheme_name: str,
        context: ClientCallContext | None,
    ) -> str | None:
        """
        Retrieves a credential (e.g., token) for a security scheme.
        """
        pass


class InMemoryContextCredentialStore(CredentialService):
    """
    A simple in-memory store for context-keyed credentials.

    This class uses the 'contextId' from the ClientCallContext state to
    store and retrieve credentials, providing a simple, user-specific
    credential mechanism without requiring a full user authentication system.
    """

    def __init__(self):
        # {context_id: {scheme_name: credential}}
        self._store: dict[str, dict[str, str]] = {}

    async def get_credentials(
        self,
        security_scheme_name: str,
        context: ClientCallContext | None,
    ) -> str | None:
        if not context or 'contextId' not in context.state:
            return None
        context_id = context.state['contextId']
        return self._store.get(context_id, {}).get(security_scheme_name)

    async def set_credentials(
        self, context_id: str, security_scheme_name: str, credential: str
    ):
        """Method to populate the store."""
        if context_id not in self._store:
            self._store[context_id] = {}
        self._store[context_id][security_scheme_name] = credential