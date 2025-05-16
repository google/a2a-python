import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import httpx
from httpx_sse import SSEError, aconnect_sse

from a2a.client.errors import A2AClientHTTPError, A2AClientJSONError
from a2a.types import (
    AgentCard,
    CancelTaskRequest,
    CancelTaskResponse,
    GetTaskPushNotificationConfigRequest,
    GetTaskPushNotificationConfigResponse,
    GetTaskRequest,
    GetTaskResponse,
    SendMessageRequest,
    SendMessageResponse,
    SendStreamingMessageRequest,
    SendStreamingMessageResponse,
    SetTaskPushNotificationConfigRequest,
    SetTaskPushNotificationConfigResponse,
)
from a2a.utils.telemetry import SpanKind, trace_class


class A2ACardResolver:
    """Agent Card resolver."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        base_url: str,
        agent_card_path: str = '/.well-known/agent.json',
        extended_agent_card_path: str = '/agent/authenticatedExtendedCard',
    ):
        self.base_url = base_url.rstrip('/')
        self.agent_card_path = agent_card_path.lstrip('/')
        self.extended_agent_card_path = extended_agent_card_path.lstrip('/')
        self.httpx_client = httpx_client

    async def get_agent_card(
        self, http_kwargs: dict[str, Any] | None = None
    ) -> AgentCard:
        # Fetch the initial public agent card
        public_card_url = f'{self.base_url}/{self.agent_card_path}'
        try:
            response = await self.httpx_client.get(
                public_card_url,
                **(http_kwargs or {}),
            )
            response.raise_for_status()
            public_agent_card_data = response.json()
            logger.info("Successfully fetched public agent card data: %s", public_agent_card_data) # Added for verbosity
            # print(f"DEBUG: Fetched public agent card data:\n{json.dumps(public_agent_card_data, indent=2)}") # Added for direct output
            agent_card = AgentCard.model_validate(public_agent_card_data)
        except httpx.HTTPStatusError as e:
            raise A2AClientHTTPError(
                e.response.status_code,
                f'Failed to fetch public agent card from {public_card_url}: {e}',
            ) from e
        except json.JSONDecodeError as e:
            raise A2AClientJSONError(
                f'Failed to parse JSON for public agent card from {public_card_url}: {e}'
            ) from e
        except httpx.RequestError as e:
            raise A2AClientHTTPError(
                503,
                f'Network communication error fetching public agent card from {public_card_url}: {e}',
            ) from e

        # Check for supportsAuthenticatedExtendedCard
        if agent_card.supportsAuthenticatedExtendedCard:
            # Construct URL for the extended card.
            # The extended card URL is relative to the agent's base URL specified *in* the agent card.
            if not agent_card.url:
                logger.warning(
                    "Agent card (from %s) indicates support for an extended card "
                    "but does not specify its own base 'url' field. "
                    "Cannot fetch extended card. Proceeding with public card.",
                    public_card_url,
                )
                return agent_card

            extended_card_base_url = agent_card.url.rstrip('/')
            full_extended_card_url = (
                f'{extended_card_base_url}/{self.extended_agent_card_path}'
            )

            logger.info(
                'Attempting to fetch extended agent card from %s',
                full_extended_card_url,
            )
            try:
                # Make another GET request for the extended card
                # Note: Authentication headers will be added here when auth is implemented.
                extended_response = await self.httpx_client.get(
                    full_extended_card_url,
                    **(http_kwargs or {}),  # Passing original http_kwargs
                )
                extended_response.raise_for_status()
                extended_agent_card_data = extended_response.json()
                logger.info("Successfully fetched extended agent card data: %s", extended_agent_card_data) # Added for verbosity
                print(f"DEBUG: Fetched extended agent card data:\n{json.dumps(extended_agent_card_data, indent=2)}") # Added for direct output
                # This new card data replaces the old one entirely
                agent_card = AgentCard.model_validate(extended_agent_card_data)
                logger.info(
                    'Successfully fetched and using extended agent card from %s',
                    full_extended_card_url,
                )
            except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, ValidationError) as e:
                logger.warning(
                    'Failed to fetch or parse extended agent card from %s. Error: %s. '
                    'Proceeding with the initially fetched public agent card.',
                    full_extended_card_url, e
                )
                # Fallback to the already parsed public_agent_card (which is 'agent_card' at this point)

        return agent_card


@trace_class(kind=SpanKind.CLIENT)
class A2AClient:
    """A2A Client."""

    def __init__(
        self,
        httpx_client: httpx.AsyncClient,
        agent_card: AgentCard | None = None,
        url: str | None = None,
    ):
        if agent_card:
            self.url = agent_card.url
        elif url:
            self.url = url
        else:
            raise ValueError('Must provide either agent_card or url')

        self.httpx_client = httpx_client

    @staticmethod
    async def get_client_from_agent_card_url(
        httpx_client: httpx.AsyncClient,
        base_url: str,
        agent_card_path: str = '/.well-known/agent.json',
        http_kwargs: dict[str, Any] | None = None,
    ) -> 'A2AClient':
        """Get a A2A client for provided agent card URL."""
        agent_card: AgentCard = await A2ACardResolver(
            httpx_client, base_url=base_url, agent_card_path=agent_card_path
        ).get_agent_card(http_kwargs=http_kwargs)
        return A2AClient(httpx_client=httpx_client, agent_card=agent_card)

    async def send_message(
        self,
        request: SendMessageRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> SendMessageResponse:
        if not request.id:
            request.id = str(uuid4())

        return SendMessageResponse(
            **await self._send_request(
                request.model_dump(mode='json', exclude_none=True),
                http_kwargs,
            )
        )

    async def send_message_streaming(
        self,
        request: SendStreamingMessageRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> AsyncGenerator[SendStreamingMessageResponse]:
        if not request.id:
            request.id = str(uuid4())

        # Default to no timeout for streaming, can be overridden by http_kwargs
        http_kwargs_with_timeout: dict[str, Any] = {
            'timeout': None,
            **(http_kwargs or {}),
        }

        async with aconnect_sse(
            self.httpx_client,
            'POST',
            self.url,
            json=request.model_dump(mode='json', exclude_none=True),
            **http_kwargs_with_timeout,
        ) as event_source:
            try:
                async for sse in event_source.aiter_sse():
                    yield SendStreamingMessageResponse(**json.loads(sse.data))
            except SSEError as e:
                raise A2AClientHTTPError(
                    400,
                    f'Invalid SSE response or protocol error: {e}',
                ) from e
            except json.JSONDecodeError as e:
                raise A2AClientJSONError(str(e)) from e
            except httpx.RequestError as e:
                raise A2AClientHTTPError(
                    503, f'Network communication error: {e}'
                ) from e

    async def _send_request(
        self,
        rpc_request_payload: dict[str, Any],
        http_kwargs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Sends a non-streaming JSON-RPC request to the agent.

        Args:
            rpc_request_payload: JSON RPC payload for sending the request
            **kwargs: Additional keyword arguments to pass to the httpx client.
        """
        try:
            response = await self.httpx_client.post(
                self.url, json=rpc_request_payload, **(http_kwargs or {})
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise A2AClientHTTPError(e.response.status_code, str(e)) from e
        except json.JSONDecodeError as e:
            raise A2AClientJSONError(str(e)) from e
        except httpx.RequestError as e:
            raise A2AClientHTTPError(
                503, f'Network communication error: {e}'
            ) from e

    async def get_task(
        self,
        request: GetTaskRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> GetTaskResponse:
        if not request.id:
            request.id = str(uuid4())

        return GetTaskResponse(
            **await self._send_request(
                request.model_dump(mode='json', exclude_none=True),
                http_kwargs,
            )
        )

    async def cancel_task(
        self,
        request: CancelTaskRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> CancelTaskResponse:
        if not request.id:
            request.id = str(uuid4())

        return CancelTaskResponse(
            **await self._send_request(
                request.model_dump(mode='json', exclude_none=True),
                http_kwargs,
            )
        )

    async def set_task_callback(
        self,
        request: SetTaskPushNotificationConfigRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> SetTaskPushNotificationConfigResponse:
        if not request.id:
            request.id = str(uuid4())

        return SetTaskPushNotificationConfigResponse(
            **await self._send_request(
                request.model_dump(mode='json', exclude_none=True),
                http_kwargs,
            )
        )

    async def get_task_callback(
        self,
        request: GetTaskPushNotificationConfigRequest,
        *,
        http_kwargs: dict[str, Any] | None = None,
    ) -> GetTaskPushNotificationConfigResponse:
        if not request.id:
            request.id = str(uuid4())

        return GetTaskPushNotificationConfigResponse(
            **await self._send_request(
                request.model_dump(mode='json', exclude_none=True),
                http_kwargs,
            )
        )
