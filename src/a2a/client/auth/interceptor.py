# a2a/client/auth/interceptor.py

import logging
from typing import Any

from a2a.client.auth.credentials import CredentialService
from a2a.client.middleware import ClientCallContext, ClientCallInterceptor
from a2a.types import AgentCard, APIKeySecurityScheme, HTTPAuthSecurityScheme, In, OAuth2SecurityScheme

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
        if not agent_card or not agent_card.security or not agent_card.securitySchemes:
            return request_payload, http_kwargs

        for requirement in agent_card.security:
            for scheme_name in requirement: # Iterate through scheme names in the requirement
                credential = await self._credential_service.get_credentials(
                    scheme_name, context
                )
                if credential and scheme_name in agent_card.securitySchemes:
                    scheme_def_union = agent_card.securitySchemes[scheme_name]
                    if not scheme_def_union:
                        continue 
                    scheme_def = scheme_def_union.root # SecurityScheme is a RootModel

                    headers = http_kwargs.get('headers', {})

                    if isinstance(scheme_def, HTTPAuthSecurityScheme):
                        if scheme_def.scheme.lower() == 'bearer':
                            headers['Authorization'] = f"Bearer {credential}"
                            logger.debug(f"Added HTTP Bearer Auth for scheme '{scheme_name}'.")
                            http_kwargs['headers'] = headers
                            return request_payload, http_kwargs
                    elif isinstance(scheme_def, OAuth2SecurityScheme): # New condition for OAuth2
                        # For OAuth2, the credential obtained is the access token, used as a Bearer token.
                        headers['Authorization'] = f"Bearer {credential}"
                        logger.debug(f"Added OAuth2 Bearer token for scheme '{scheme_name}'.")
                        http_kwargs['headers'] = headers
                        return request_payload, http_kwargs
                    elif isinstance(scheme_def, APIKeySecurityScheme):
                        if scheme_def.in_ == In.header: # Use In.header enum member
                            headers[scheme_def.name] = credential
                            logger.debug(f"Added API Key Header for scheme '{scheme_name}'.")
                            http_kwargs['headers'] = headers
                            return request_payload, http_kwargs
                        # Note: API keys in query or cookie are not handled by this interceptor modification.
        
        return request_payload, http_kwargs