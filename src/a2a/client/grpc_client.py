import logging

from collections.abc import AsyncGenerator, AsyncIterator

import grpc

from a2a.client.client import (
    Client,
    ClientCallContext,
    ClientConfig,
    Consumer,
    ClientEvent,
)
from a2a.client.middleware import ClientCallInterceptor
from a2a.client.client_task_manager import ClientTaskManager
from a2a.grpc import a2a_pb2, a2a_pb2_grpc
from a2a.types import (
    AgentCard,
    GetTaskPushNotificationConfigParams,
    Message,
    MessageSendParams,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskStatusUpdateEvent,
)
from a2a.utils import proto_utils
from a2a.utils.telemetry import SpanKind, trace_class


logger = logging.getLogger(__name__)


#@trace_class(kind=SpanKind.CLIENT)
class GrpcTransportClient:
    """Transport specific details for interacting with an A2A agent via gRPC."""

    def __init__(
        self,
        grpc_stub: a2a_pb2_grpc.A2AServiceStub,
        agent_card: AgentCard | None,
    ):
        """Initializes the GrpcTransportClient.

        Requires an `AgentCard` and a grpc `A2AServiceStub`.

        Args:
            grpc_stub: A grpc client stub.
            agent_card: The agent card object.
        """
        self.agent_card = agent_card
        self.stub = grpc_stub
        # If they don't provide an agent card, but do have a stub, lookup the
        # card from the stub.
        self._needs_extended_card = (
            agent_card.supportsAuthenticatedExtendedCard
            if agent_card else True
        )

    async def send_message(
        self,
        request: MessageSendParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task | Message:
        """Sends a non-streaming message request to the agent.

        Args:
            request: The `MessageSendParams` object containing the message and configuration.

        Returns:
            A `Task` or `Message` object containing the agent's response.
        """
        response = await self.stub.SendMessage(
            a2a_pb2.SendMessageRequest(
                request=proto_utils.ToProto.message(request.message),
                configuration=proto_utils.ToProto.message_send_configuration(
                    request.configuration
                ),
                metadata=proto_utils.ToProto.metadata(request.metadata),
            )
        )
        if response.task:
            return proto_utils.FromProto.task(response.task)
        return proto_utils.FromProto.message(response.msg)

    async def send_message_streaming(
        self,
        request: MessageSendParams,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncGenerator[
        Message | Task | TaskStatusUpdateEvent | TaskArtifactUpdateEvent
    ]:
        """Sends a streaming message request to the agent and yields responses as they arrive.

        This method uses gRPC streams to receive a stream of updates from the
        agent.

        Args:
            request: The `MessageSendParams` object containing the message and configuration.

        Yields:
            `Message` or `Task` or `TaskStatusUpdateEvent` or
            `TaskArtifactUpdateEvent` objects as they are received in the
            stream.
        """
        stream = self.stub.SendStreamingMessage(
            a2a_pb2.SendMessageRequest(
                request=proto_utils.ToProto.message(request.message),
                configuration=proto_utils.ToProto.message_send_configuration(
                    request.configuration
                ),
                metadata=proto_utils.ToProto.metadata(request.metadata),
            )
        )
        while True:
            response = await stream.read()
            if response == grpc.aio.EOF:  # pyright: ignore [reportAttributeAccessIssue]
                break
            if response.HasField('msg'):
                yield proto_utils.FromProto.message(response.msg)
            elif response.HasField('task'):
                yield proto_utils.FromProto.task(response.task)
            elif response.HasField('status_update'):
                yield proto_utils.FromProto.task_status_update_event(
                    response.status_update
                )
            elif response.HasField('artifact_update'):
                yield proto_utils.FromProto.task_artifact_update_event(
                    response.artifact_update
                )

    async def get_task(
        self,
        request: TaskQueryParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        """Retrieves the current state and history of a specific task.

        Args:
            request: The `TaskQueryParams` object specifying the task ID

        Returns:
            A `Task` object containing the Task or None.
        """
        task = await self.stub.GetTask(
            a2a_pb2.GetTaskRequest(name=f'tasks/{request.id}')
        )
        return proto_utils.FromProto.task(task)

    async def cancel_task(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        """Requests the agent to cancel a specific task.

        Args:
            request: The `TaskIdParams` object specifying the task ID.

        Returns:
            A `Task` object containing the updated Task
        """
        task = await self.stub.CancelTask(
            a2a_pb2.CancelTaskRequest(name=f'tasks/{request.id}')
        )
        return proto_utils.FromProto.task(task)

    async def set_task_callback(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        """Sets or updates the push notification configuration for a specific task.

        Args:
            request: The `TaskPushNotificationConfig` object specifying the task ID and configuration.

        Returns:
            A `TaskPushNotificationConfig` object containing the config.
        """
        config = await self.stub.CreateTaskPushNotificationConfig(
            a2a_pb2.CreateTaskPushNotificationConfigRequest(
                parent='',
                config_id='',
                config=proto_utils.ToProto.task_push_notification_config(
                    request
                ),
            )
        )
        return proto_utils.FromProto.task_push_notification_config(config)

    async def get_task_callback(
        self,
        request: TaskIdParams,  # TODO: Update to a push id params
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        """Retrieves the push notification configuration for a specific task.

        Args:
            request: The `TaskIdParams` object specifying the task ID.

        Returns:
            A `TaskPushNotificationConfig` object containing the configuration.
        """
        config = await self.stub.GetTaskPushNotificationConfig(
            a2a_pb2.GetTaskPushNotificationConfigRequest(
                name=f'tasks/{request.id}/pushNotification/undefined',
            )
        )
        return proto_utils.FromProto.task_push_notification_config(config)

    async def get_card(
        self,
        *,
        context: ClientCallContext | None = None,
    ) -> AgentCard:
        """Retrieves the authenticated card (if necessary) or the public one.

        Args:
            context: The client call context.

        Returns:
            A `AgentCard` object containing the card.

        Raises:
            grpc.RpcError: If a gRPC error occurs during the request.
        """
        # If we don't have the public card, try to get that first.
        card = self.agent_card

        if not self._needs_extended_card:
            return card

        card_pb = await self.stub.GetAgentCard(
            a2a_pb2.GetAgentCardRequest(),
        )
        card =  proto_utils.FromProto.agent_card(card_pb)
        self.agent_card = card
        self._needs_extended_card = False
        return card


#@trace_class(kind=SpanKind.CLIENT)
class GrpcClient(Client):
    """GrpcClient provides the Client interface for the gRPC transport."""

    def __init__(
        self,
        card: AgentCard,
        config: ClientConfig,
        consumers: list[Consumer],
        middleware: list[ClientCallInterceptor],
    ):
        super().__init__(consumers, middleware)
        if not config.grpc_channel_factory:
            raise Exception('GRPC client requires channel factory.')
        self._card = card
        self._config = config
        # Defer init to first use.
        self._transport_client = None
        channel = self._config.grpc_channel_factory(self._card.url)
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        self._transport_client = GrpcTransportClient(stub, self._card)

    async def send_message(
        self,
        request: Message,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[ClientEvent | Message]:
        # TODO: Set the request params from config
        if not self._config.streaming or not self._card.capabilities.streaming:
            print("Using blocking interaction")
            response = await self._transport_client.send_message(
                MessageSendParams(
                    message=request,
                    # TODO: set params
                ),
                context=context,
            )
            result = (
                (response, None) if isinstance(response, Task) else response
            )
            # Spin off consumers - in thread, out of thread, etc?
            await self.consume(result, self._card)
            yield result
            return
        # Get Task tracker
        print("Using streaming interactions")
        tracker = ClientTaskManager()
        async for event in self._transport_client.send_message_streaming(
            MessageSendParams(
                message=request,
                # TODO: set params
            ),
            context=context,
        ):
            # Update task, check for errors, etc.
            if isinstance(event, Message):
                await self.consume(event, self._card)
                yield event
                return
            await tracker.process(event)
            result = (
                tracker.get_task(),
                None if isinstance(event, Task) else event
            )
            await self.consume(result, self._card)
            yield result

    async def get_task(
        self,
        request: TaskQueryParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        response = await self._transport_client.get_task(
            request,
            context=context,
        )
        return response

    async def cancel_task(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> Task:
        response = await self._transport_client.cancel_task(
            request,
            context=context,
        )
        return response

    async def set_task_callback(
        self,
        request: TaskPushNotificationConfig,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        response = await self._transport_client.set_task_callback(
            request,
            context=context,
        )
        return response

    async def get_task_callback(
        self,
        request: GetTaskPushNotificationConfigParams,
        *,
        context: ClientCallContext | None = None,
    ) -> TaskPushNotificationConfig:
        response = await self._transport_client.get_task_callback(
            request,
            context=context,
        )
        return response

    async def resubscribe(
        self,
        request: TaskIdParams,
        *,
        context: ClientCallContext | None = None,
    ) -> AsyncIterator[Task | Message]:
        if not self._config.streaming or not self._card.capabilities.streaming:
            raise Exception(
                'client and/or server do not support resubscription.'
            )
        async for event in self._transport_client.resubscribe(
            request,
            context=context,
        ):
            # Update task, check for errors, etc.
            yield event

    async def get_card(
        self,
        *,
        context: ClientCallContext | None = None,
    ) -> AgentCard:
        card = await self._transport_client.get_card(
            context=context,
        )
        self._card = card
        return card


def NewGrpcClient(
    card: AgentCard,
    config: ClientConfig,
    consumers: list[Consumer],
    middleware: list[ClientCallInterceptor]
) -> Client:
    return GrpcClient(card, config, consumers, middleware)
