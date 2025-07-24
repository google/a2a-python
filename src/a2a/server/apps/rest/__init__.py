"""A2A REST Applications."""

from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.apps.rest.rest_app import RESTApplication


__all__ = [
    'A2ARESTFastAPIApplication',
    'RESTApplication',
]
