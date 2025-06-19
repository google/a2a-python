"""Helper functions for handling optional FastAPI package imports."""

try:
    from fastapi import FastAPI, Request, Response
except ImportError:
    _FASTAPI_DEPENDENCY_ERROR_MSG = """
    The A2A Python SDK FastAPI app requires the FastAPI package, which
    is an optional dependency. To fix this issue, please add the fastapi
    package to your project, e.g. by executing

        uv add fastapi

    or install the A2A SDK with the optional FastAPI dependency:

        uv add a2a-sdk[fastapi]
    """

    class _DummyFastAPIClasses:
        """Parent class for dummy fastapi.* class declarations."""

        def __init__(self) -> None:
            """Raises ImportError when initiating a dummy fastapi.* instance."""
            raise ImportError(_FASTAPI_DEPENDENCY_ERROR_MSG)

    class FastAPI(_DummyFastAPIClasses):  # type: ignore[no-redef]
        """A dummy fastapi.FastAPI declaration."""

    class Request(_DummyFastAPIClasses):  # type: ignore[no-redef]
        """A dummy fastapi.Request declaration."""

    class Response(_DummyFastAPIClasses):  # type: ignore[no-redef]
        """A dummy fastapi.Response declaration."""
