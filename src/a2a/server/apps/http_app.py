from abc import ABC, abstractmethod
from typing import Any

from starlette.applications import Starlette


class HttpApp(ABC):
    """A2A Server application interface.

    Defines the interface for building an HTTP application that serves
    the A2A protocol.
    """

    @abstractmethod
    def build(self, **kwargs: Any) -> Starlette:
        """Builds and returns a Starlette application instance.

        Args:
            **kwargs: Additional keyword arguments to pass to the Starlette
              constructor.

        Returns:
            A configured Starlette application instance.
        """
