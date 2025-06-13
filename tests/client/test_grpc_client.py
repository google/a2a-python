from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from a2a.client import A2AGrpcClient
from a2a.grpc import a2a_pb2, a2a_pb2_grpc
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    PushNotificationConfig,
    Role,
    Task,
    TaskArtifactUpdateEvent,
    TaskIdParams,
    TaskPushNotificationConfig,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2a.utils import proto_utils


# Fixtures
@pytest.fixture
def mock_grpc_stub() -> AsyncMock:
    """Provides a mock gRPC stub."""
    return AsyncMock(spec=a2a_pb2_grpc.A2AServiceStub)


@pytest.fixture
def sample_agent_card() -> AgentCard:
    """Provides a minimal agent card for initialization."""
    return AgentCard(
        name='gRPC Test Agent',
        description='Agent for testing gRPC client',
        url='grpc://localhost:50051',
        version='1.0',
        capabilities=AgentCapabilities(streaming=True, pushNotifications=True),
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        skills=[],
    )


@pytest.fixture
def grpc_client(
    mock_grpc_stub: AsyncMock, sample_agent_card: AgentCard
) -> A2AGrpcClient:
    """Provides an A2AGrpcClient instance."""
    return A2AGrpcClient(grpc_stub=mock_grpc_stub, agent_card=sample_agent_card)


@pytest.fixture
def sample_message_send_params() -> MessageSendParams:
    """Provides a sample MessageSendParams object."""
    return MessageSendParams(
        message=Message(
            role=Role.user,
            messageId='msg-1',
            parts=[Part(root=TextPart(text='Hello'))],
        )
    )


@pytest.fixture
def sample_task() -> Task:
    """Provides a sample Task object."""
    return Task(
        id='task-1',
        contextId='ctx-1',
        status=TaskStatus(state=TaskState.completed),
    )


@pytest.fixture
def sample_message() -> Message:
    """Provides a sample Message object."""
    return Message(
        role=Role.agent,
        messageId='msg-response',
        parts=[Part(root=TextPart(text='Hi there'))],
    )


@pytest.mark.asyncio
async def test_send_message_task_response(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_message_send_params: MessageSendParams,
    sample_task: Task,
):
    """Test send_message that returns a Task."""
    mock_grpc_stub.SendMessage.return_value = a2a_pb2.SendMessageResponse(
        task=proto_utils.ToProto.task(sample_task)
    )

    response = await grpc_client.send_message(sample_message_send_params)

    mock_grpc_stub.SendMessage.assert_awaited_once()
    assert isinstance(response, Task)
    assert response.id == sample_task.id


@pytest.mark.asyncio
async def test_send_message_message_response(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_message_send_params: MessageSendParams,
    sample_message: Message,
):
    """Test send_message that returns a Message."""
    mock_grpc_stub.SendMessage.return_value = a2a_pb2.SendMessageResponse(
        msg=proto_utils.ToProto.message(sample_message)
    )

    response = await grpc_client.send_message(sample_message_send_params)

    mock_grpc_stub.SendMessage.assert_awaited_once()
    assert isinstance(response, Message)
    assert response.messageId == sample_message.messageId


@pytest.mark.asyncio
async def test_send_message_streaming(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_message_send_params: MessageSendParams,
):
    """Test the streaming message functionality."""
    mock_stream = AsyncMock()

    status_update = TaskStatusUpdateEvent(
        taskId='task-stream',
        contextId='ctx-stream',
        status=TaskStatus(state=TaskState.working),
        final=False,
    )
    artifact_update = TaskArtifactUpdateEvent(
        taskId='task-stream',
        contextId='ctx-stream',
        artifact=MagicMock(spec=types.Artifact),
    )
    final_task = Task(
        id='task-stream',
        contextId='ctx-stream',
        status=TaskStatus(state=TaskState.completed),
    )

    stream_responses = [
        a2a_pb2.StreamResponse(
            status_update=proto_utils.ToProto.task_status_update_event(
                status_update
            )
        ),
        a2a_pb2.StreamResponse(
            artifact_update=proto_utils.ToProto.task_artifact_update_event(
                artifact_update
            )
        ),
        a2a_pb2.StreamResponse(task=proto_utils.ToProto.task(final_task)),
        grpc.aio.EOF,
    ]

    mock_stream.read.side_effect = stream_responses
    mock_grpc_stub.SendStreamingMessage.return_value = mock_stream

    results = [
        result
        async for result in grpc_client.send_message_streaming(
            sample_message_send_params
        )
    ]

    mock_grpc_stub.SendStreamingMessage.assert_called_once()
    assert len(results) == 3
    assert isinstance(results[0], TaskStatusUpdateEvent)
    assert isinstance(results[1], TaskArtifactUpdateEvent)
    assert isinstance(results[2], Task)
    assert results[2].status.state == TaskState.completed


@pytest.mark.asyncio
async def test_get_task(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock, sample_task: Task
):
    """Test retrieving a task."""
    mock_grpc_stub.GetTask.return_value = proto_utils.ToProto.task(sample_task)
    params = TaskQueryParams(id=sample_task.id)

    response = await grpc_client.get_task(params)

    mock_grpc_stub.GetTask.assert_awaited_once_with(
        a2a_pb2.GetTaskRequest(name=f'tasks/{sample_task.id}')
    )
    assert response.id == sample_task.id


@pytest.mark.asyncio
async def test_cancel_task(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock, sample_task: Task
):
    """Test cancelling a task."""
    cancelled_task = sample_task.model_copy()
    cancelled_task.status.state = TaskState.canceled
    mock_grpc_stub.CancelTask.return_value = proto_utils.ToProto.task(
        cancelled_task
    )
    params = TaskIdParams(id=sample_task.id)

    response = await grpc_client.cancel_task(params)

    mock_grpc_stub.CancelTask.assert_awaited_once_with(
        a2a_pb2.CancelTaskRequest(name=f'tasks/{sample_task.id}')
    )
    assert response.status.state == TaskState.canceled


@pytest.mark.asyncio
async def test_set_task_callback(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test setting a task callback."""
    task_id = 'task-callback-1'
    config = TaskPushNotificationConfig(
        taskId=task_id,
        pushNotificationConfig=PushNotificationConfig(
            url='http://my.callback/push', token='secret'
        ),
    )
    proto_config = proto_utils.ToProto.task_push_notification_config(config)
    mock_grpc_stub.CreateTaskPushNotification.return_value = proto_config

    response = await grpc_client.set_task_callback(config)

    mock_grpc_stub.CreateTaskPushNotification.assert_awaited_once()
    call_args, _ = mock_grpc_stub.CreateTaskPushNotification.call_args
    sent_request = call_args[0]
    assert isinstance(sent_request, a2a_pb2.CreateTaskPushNotificationRequest)

    assert response.taskId == task_id
    assert response.pushNotificationConfig.url == 'http://my.callback/push'


@pytest.mark.asyncio
async def test_get_task_callback(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test getting a task callback."""
    task_id = 'task-get-callback-1'
    push_id = 'undefined'  # As per current implementation
    resource_name = f'tasks/{task_id}/pushNotification/{push_id}'

    config = TaskPushNotificationConfig(
        taskId=task_id,
        pushNotificationConfig=PushNotificationConfig(
            url='http://my.callback/get', token='secret-get'
        ),
    )
    proto_config = proto_utils.ToProto.task_push_notification_config(config)
    mock_grpc_stub.GetTaskPushNotification.return_value = proto_config

    params = TaskIdParams(id=task_id)
    response = await grpc_client.get_task_callback(params)

    mock_grpc_stub.GetTaskPushNotification.assert_awaited_once_with(
        a2a_pb2.GetTaskPushNotificationRequest(name=resource_name)
    )
    assert response.taskId == task_id
    assert response.pushNotificationConfig.url == 'http://my.callback/get'


@pytest.mark.asyncio
async def test_send_message_streaming_with_msg_and_task(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_message_send_params: MessageSendParams,
):
    """Test streaming response that contains both message and task types."""
    mock_stream = AsyncMock()

    msg_event = Message(role=Role.agent, messageId='msg-stream-1', parts=[])
    task_event = Task(
        id='task-stream-1',
        contextId='ctx-stream-1',
        status=TaskStatus(state=TaskState.completed),
    )

    stream_responses = [
        a2a_pb2.StreamResponse(msg=proto_utils.ToProto.message(msg_event)),
        a2a_pb2.StreamResponse(task=proto_utils.ToProto.task(task_event)),
        grpc.aio.EOF,
    ]

    mock_stream.read.side_effect = stream_responses
    mock_grpc_stub.SendStreamingMessage.return_value = mock_stream

    results = [
        result
        async for result in grpc_client.send_message_streaming(
            sample_message_send_params
        )
    ]

    assert len(results) == 2
    assert isinstance(results[0], Message)
    assert isinstance(results[1], Task)
