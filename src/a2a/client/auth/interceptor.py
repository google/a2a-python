# a2a/client/auth/interceptor.py

import logging
from typing import Any

from a2a.client.auth.credentials import CredentialService
from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.types import AgentCard, APIKeySecurityScheme, HTTPAuthSecurityScheme

logger = logging.getLogger(__name__)


class AuthInterceptor(ClientCallInterceptor):
    """
    An interceptor that automatically adds authentication details to requests
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
        """
        Adds authentication headers to the request if credentials can be found.
        """
        if not agent_card or not agent_card.security or not agent_card.securitySchemes:
            return request_payload, http_kwargs

        for requirement in agent_card.security:
            for scheme_name in requirement:
                credential = await self._credential_service.get_credentials(
                    scheme_name, context
                )
                if credential and scheme_name in agent_card.securitySchemes:
                    scheme_def = agent_card.securitySchemes[scheme_name].root
                    headers = http_kwargs.get('headers', {})

                    if isinstance(scheme_def, HTTPAuthSecurityScheme):
                        headers['Authorization'] = f"{scheme_def.scheme} {credential}"
                        http_kwargs['headers'] = headers
                        logger.debug(f"Added HTTP Auth for scheme '{scheme_name}'.")
                        return request_payload, http_kwargs
                    elif isinstance(scheme_def, APIKeySecurityScheme):
                        if scheme_def.in_ == 'header':
                            headers[scheme_def.name] = credential
                            http_kwargs['headers'] = headers
                            logger.debug(f"Added API Key Header for scheme '{scheme_name}'.")
                            return request_payload, http_kwargs
                        else:
                            logger.warning(
                                f"API Key in '{scheme_def.in_}' not supported by this interceptor."
                            )

        return request_payload, http_kwargs