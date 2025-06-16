import logging

from typing import Any

from a2a.client.auth.credentials import CredentialService
from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.types import (
    APIKeySecurityScheme,
    AgentCard,
    HTTPAuthSecurityScheme,
    In,
    OAuth2SecurityScheme,
    OpenIdConnectSecurityScheme,
)


logger = logging.getLogger(__name__)


class AuthInterceptor(ClientCallInterceptor):
    """An interceptor that automatically adds authentication details to requests
    based on the agent's security schemes.
    """

    def __init__(self, credential_service: CredentialService):
        self._credential_service = credential_service

    async def intercept(
        self,
        method_name: str,
        request_payload: dict[str, Any],
        http_kwargs: dict[str, Any],
        agent_card: AgentCard | None,
        context: ClientCallContext | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not all((agent_card, agent_card.security, agent_card.securitySchemes)):
            return request_payload, http_kwargs

        for requirement in agent_card.security:
            for scheme_name in requirement:
                credential = await self._credential_service.get_credentials(
                    scheme_name, context
                )
                if credential and scheme_name in agent_card.securitySchemes:
                    scheme_def_union = agent_card.securitySchemes[scheme_name]
                    if not scheme_def_union:
                        continue
                    scheme_def = scheme_def_union.root

                    headers = http_kwargs.get('headers', {})

                    is_bearer_scheme = False
                    if (
                        isinstance(scheme_def, HTTPAuthSecurityScheme)
                        and scheme_def.scheme.lower() == 'bearer'
                    ) or isinstance(
                        scheme_def,
                        OAuth2SecurityScheme | OpenIdConnectSecurityScheme,
                    ):
                        is_bearer_scheme = True

                    if is_bearer_scheme:
                        headers['Authorization'] = f'Bearer {credential}'
                        logger.debug(
                            f"Added Bearer token for scheme '{scheme_name}' (type: {scheme_def.type})."
                        )
                        http_kwargs['headers'] = headers
                        return request_payload, http_kwargs
                    if isinstance(scheme_def, APIKeySecurityScheme):
                        if scheme_def.in_ == In.header:
                            headers[scheme_def.name] = credential
                            logger.debug(
                                f"Added API Key Header for scheme '{scheme_name}'."
                            )
                            http_kwargs['headers'] = headers
                            return request_payload, http_kwargs
                        # Note: API keys in query or cookie are not handled here.

        return request_payload, http_kwargs
