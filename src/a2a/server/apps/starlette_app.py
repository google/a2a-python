import json
import logging
import traceback

from collections.abc import AsyncGenerator
from typing import Any

from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.request_handlers.jsonrpc_handler import JSONRPCHandler

from a2a.types import (
    A2AError,
    A2ARequest,
    AgentCard,
    CancelTaskRequest,
    GetTaskPushNotificationConfigRequest,
    GetTaskRequest,
    InternalError,
    InvalidRequestError,
    JSONParseError,
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCResponse,
    SendMessageRequest,
    SendStreamingMessageRequest,
    SendStreamingMessageResponse,
    SetTaskPushNotificationConfigRequest,
    TaskResubscriptionRequest,
    UnsupportedOperationError,
)
from a2a.utils.errors import MethodNotImplementedError


logger = logging.getLogger(__name__)


class A2AStarletteApplication:
    """A Starlette application implementing the A2A protocol server endpoints.

    Handles incoming JSON-RPC requests, routes them to the appropriate
    handler methods, and manages response generation including Server-Sent Events
    (SSE).
    """

    def __init__(self, agent_card: AgentCard, http_handler: RequestHandler):
        """Initializes the A2AStarletteApplication.

        Args:
            agent_card: The AgentCard describing the agent's capabilities.
            http_handler: The handler instance responsible for processing A2A
              requests via http.
        """
        self.agent_card = agent_card
        self.handler = JSONRPCHandler(
            agent_card=agent_card, request_handler=http_handler
        )

    def _generate_error_response(
        self, request_id: str | int | None, error: JSONRPCError | A2AError
    ) -> JSONResponse:
        """Creates a Starlette JSONResponse for a JSON-RPC error.

        Logs the error based on its type.

        Args:
            request_id: The ID of the request that caused the error.
            error: The `JSONRPCError` or `A2AError` object.

        Returns:
            A `JSONResponse` object formatted as a JSON-RPC error response.
        """
        error_resp = JSONRPCErrorResponse(
            id=request_id,
            error=error if isinstance(error, JSONRPCError) else error.root,
        )

        log_level = (
            logging.ERROR
            if not isinstance(error, A2AError)
            or isinstance(error.root, InternalError)
            else logging.WARNING
        )
        logger.log(
            log_level,
            f'Request Error (ID: {request_id}): '
            f"Code={error_resp.error.code}, Message='{error_resp.error.message}'"
            f'{", Data=" + str(error_resp.error.data) if hasattr(error, "data") and error_resp.error.data else ""}',
        )
        return JSONResponse(
            error_resp.model_dump(mode='json', exclude_none=True),
            status_code=200,
        )

    async def _handle_requests(self, request: Request) -> Response:
        """Handles incoming POST requests to the main A2A endpoint.

        Parses the request body as JSON, validates it against A2A request types,
        dispatches it to the appropriate handler method, and returns the response.
        Handles JSON parsing errors, validation errors, and other exceptions,
        returning appropriate JSON-RPC error responses.

        Args:
            request: The incoming Starlette Request object.

        Returns:
            A Starlette Response object (JSONResponse or EventSourceResponse).

        Raises:
            (Implicitly handled): Various exceptions are caught and converted
            into JSON-RPC error responses by this method.
        """
        request_id = None
        body = None

        try:
            body = await request.json()
            a2a_request = A2ARequest.model_validate(body)

            request_id = a2a_request.root.id
            request_obj = a2a_request.root

            if isinstance(
                request_obj,
                TaskResubscriptionRequest | SendStreamingMessageRequest,
            ):
                return await self._process_streaming_request(
                    request_id, a2a_request
                )

            return await self._process_non_streaming_request(
                request_id, a2a_request
            )
        except MethodNotImplementedError:
            traceback.print_exc()
            return self._generate_error_response(
                request_id, A2AError(root=UnsupportedOperationError())
            )
        except json.decoder.JSONDecodeError as e:
            traceback.print_exc()
            return self._generate_error_response(
                None, A2AError(root=JSONParseError(message=str(e)))
            )
        except ValidationError as e:
            traceback.print_exc()
            return self._generate_error_response(
                request_id,
                A2AError(root=InvalidRequestError(data=json.loads(e.json()))),
            )
        except Exception as e:
            logger.error(f'Unhandled exception: {e}')
            traceback.print_exc()
            return self._generate_error_response(
                request_id, A2AError(root=InternalError(message=str(e)))
            )

    async def _process_streaming_request(
        self, request_id: str | int | None, a2a_request: A2ARequest
    ) -> Response:
        """Processes streaming requests (message/stream or tasks/resubscribe).

        Args:
            request_id: The ID of the request.
            a2a_request: The validated A2ARequest object.

        Returns:
            An `EventSourceResponse` object to stream results to the client.
        """
        request_obj = a2a_request.root
        handler_result: Any = None
        if isinstance(
            request_obj,
            SendStreamingMessageRequest,
        ):
            handler_result = self.handler.on_message_send_stream(request_obj)
        elif isinstance(request_obj, TaskResubscriptionRequest):
            handler_result = self.handler.on_resubscribe_to_task(request_obj)

        return self._create_response(handler_result)

    async def _process_non_streaming_request(
        self, request_id: str | int | None, a2a_request: A2ARequest
    ) -> Response:
        """Processes non-streaming requests (message/send, tasks/get, tasks/cancel, tasks/pushNotificationConfig/*).

        Args:
            request_id: The ID of the request.
            a2a_request: The validated A2ARequest object.

        Returns:
            A `JSONResponse` object containing the result or error.
        """
        request_obj = a2a_request.root
        handler_result: Any = None
        match request_obj:
            case SendMessageRequest():
                handler_result = await self.handler.on_message_send(request_obj)
            case CancelTaskRequest():
                handler_result = await self.handler.on_cancel_task(request_obj)
            case GetTaskRequest():
                handler_result = await self.handler.on_get_task(request_obj)
            case SetTaskPushNotificationConfigRequest():
                handler_result = await self.handler.set_push_notification(
                    request_obj
                )
            case GetTaskPushNotificationConfigRequest():
                handler_result = await self.handler.get_push_notification(
                    request_obj
                )
            case _:
                logger.error(
                    f'Unhandled validated request type: {type(request_obj)}'
                )
                error = UnsupportedOperationError(
                    message=f'Request type {type(request_obj).__name__} is unknown.'
                )
                handler_result = JSONRPCErrorResponse(
                    id=request_id, error=error
                )

        return self._create_response(handler_result)

    def _create_response(
        self,
        handler_result: (
            AsyncGenerator[SendStreamingMessageResponse]
            | JSONRPCErrorResponse
            | JSONRPCResponse
        ),
    ) -> Response:
        """Creates a Starlette Response based on the result from the request handler.

        Handles:
        - AsyncGenerator for Server-Sent Events (SSE).
        - JSONRPCErrorResponse for explicit errors returned by handlers.
        - Pydantic RootModels (like GetTaskResponse) containing success or error
        payloads.

        Args:
            handler_result: The result from a request handler method. Can be an
                async generator for streaming or a Pydantic model for non-streaming.

        Returns:
            A Starlette JSONResponse or EventSourceResponse.
        """
        if isinstance(handler_result, AsyncGenerator):
            # Result is a stream of SendStreamingMessageResponse objects
            async def event_generator(
                stream: AsyncGenerator[SendStreamingMessageResponse],
            ) -> AsyncGenerator[dict[str, str]]:
                async for item in stream:
                    yield {'data': item.root.model_dump_json(exclude_none=True)}

            return EventSourceResponse(event_generator(handler_result))
        if isinstance(handler_result, JSONRPCErrorResponse):
            return JSONResponse(
                handler_result.model_dump(
                    mode='json',
                    exclude_none=True,
                )
            )

        return JSONResponse(
            handler_result.root.model_dump(mode='json', exclude_none=True)
        )

    async def _handle_get_agent_card(self, request: Request) -> JSONResponse:
        """Handles GET requests for the agent card endpoint.

        Args:
            request: The incoming Starlette Request object.

        Returns:
            A JSONResponse containing the agent card data.
        """
        return JSONResponse(
            self.agent_card.model_dump(mode='json', exclude_none=True)
        )

    def routes(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
    ) -> list[Route]:
        """Returns the Starlette Routes for handling A2A requests.

        Args:
            agent_card_url: The URL path for the agent card endpoint.
            rpc_url: The URL path for the A2A JSON-RPC endpoint (POST requests).

        Returns:
            A list of Starlette Route objects.
        """
        return [
            Route(
                rpc_url,
                self._handle_requests,
                methods=['POST'],
                name='a2a_handler',
            ),
            Route(
                agent_card_url,
                self._handle_get_agent_card,
                methods=['GET'],
                name='agent_card',
            ),
        ]

    def build(
        self,
        agent_card_url: str = '/.well-known/agent.json',
        rpc_url: str = '/',
        **kwargs: Any,
    ) -> Starlette:
        """Builds and returns the Starlette application instance.

        Args:
            agent_card_url: The URL path for the agent card endpoint.
            rpc_url: The URL path for the A2A JSON-RPC endpoint (POST requests).
            **kwargs: Additional keyword arguments to pass to the Starlette
              constructor.

        Returns:
            A configured Starlette application instance.
        """
        routes = self.routes(agent_card_url, rpc_url)
        if 'routes' in kwargs:
            kwargs['routes'] += routes
        else:
            kwargs['routes'] = routes

        return Starlette(**kwargs)
