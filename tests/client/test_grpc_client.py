from unittest.mock import AsyncMock

import grpc
import pytest

from a2a import types
from a2a.client.grpc_client import A2AGrpcClient
from a2a.grpc import a2a_pb2, a2a_pb2_grpc


# --- Fixtures ---


@pytest.fixture
def mock_grpc_stub() -> AsyncMock:
    return AsyncMock(spec=a2a_pb2_grpc.A2AServiceStub)


@pytest.fixture
def sample_agent_card() -> types.AgentCard:
    return types.AgentCard(
        name='Test Agent',
        description='A test agent',
        url='http://localhost',
        version='1.0.0',
        capabilities=types.AgentCapabilities(
            streaming=True, pushNotifications=True
        ),
        defaultInputModes=['text/plain'],
        defaultOutputModes=['text/plain'],
        skills=[],
    )


@pytest.fixture
def grpc_client(
    mock_grpc_stub: AsyncMock, sample_agent_card: types.AgentCard
) -> A2AGrpcClient:
    return A2AGrpcClient(grpc_stub=mock_grpc_stub, agent_card=sample_agent_card)


# --- Test Cases ---


@pytest.mark.asyncio
async def test_send_message_returns_task(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test send_message when the server returns a Task."""
    request_params = types.MessageSendParams(
        message=types.Message(role=types.Role.user, messageId='1', parts=[])
    )
    response_proto = a2a_pb2.SendMessageResponse(task=a2a_pb2.Task(id='task-1'))
    mock_grpc_stub.SendMessage.return_value = response_proto

    result = await grpc_client.send_message(request_params)

    mock_grpc_stub.SendMessage.assert_awaited_once()
    assert isinstance(result, types.Task)
    assert result.id == 'task-1'


@pytest.mark.asyncio
async def test_send_message_returns_message(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test send_message when the server returns a Message."""
    request_params = types.MessageSendParams(
        message=types.Message(role=types.Role.user, messageId='1', parts=[])
    )
    response_proto = a2a_pb2.SendMessageResponse(
        msg=a2a_pb2.Message(message_id='msg-resp-1')
    )
    mock_grpc_stub.SendMessage.return_value = response_proto

    result = await grpc_client.send_message(request_params)

    mock_grpc_stub.SendMessage.assert_awaited_once()
    assert isinstance(result, types.Message)
    assert result.messageId == 'msg-resp-1'


@pytest.mark.asyncio
async def test_send_message_streaming(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test the streaming message functionality."""
    request_params = types.MessageSendParams(
        message=types.Message(role=types.Role.user, messageId='1', parts=[])
    )

    # Mock the stream object and its read method
    mock_stream = AsyncMock()
    stream_responses = [
        a2a_pb2.StreamResponse(task=a2a_pb2.Task(id='task-stream')),
        a2a_pb2.StreamResponse(msg=a2a_pb2.Message(message_id='msg-stream')),
        a2a_pb2.StreamResponse(
            status_update=a2a_pb2.TaskStatusUpdateEvent(task_id='task-stream')
        ),
        a2a_pb2.StreamResponse(
            artifact_update=a2a_pb2.TaskArtifactUpdateEvent(
                task_id='task-stream'
            )
        ),
        grpc.aio.EOF,
    ]
    mock_stream.read.side_effect = stream_responses
    mock_grpc_stub.SendStreamingMessage.return_value = mock_stream

    results = []
    async for item in grpc_client.send_message_streaming(request_params):
        results.append(item)

    mock_grpc_stub.SendStreamingMessage.assert_called_once()
    assert len(results) == 4
    assert isinstance(results[0], types.Task)
    assert isinstance(results[1], types.Message)
    assert isinstance(results[2], types.TaskStatusUpdateEvent)
    assert isinstance(results[3], types.TaskArtifactUpdateEvent)


@pytest.mark.asyncio
async def test_get_task(grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock):
    """Test retrieving a task."""
    request_params = types.TaskQueryParams(id='task-1')
    response_proto = a2a_pb2.Task(id='task-1', context_id='ctx-1')
    mock_grpc_stub.GetTask.return_value = response_proto

    result = await grpc_client.get_task(request_params)

    mock_grpc_stub.GetTask.assert_awaited_once_with(
        a2a_pb2.GetTaskRequest(name='tasks/task-1')
    )
    assert isinstance(result, types.Task)
    assert result.id == 'task-1'


@pytest.mark.asyncio
async def test_cancel_task(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test cancelling a task."""
    request_params = types.TaskIdParams(id='task-1')
    response_proto = a2a_pb2.Task(
        id='task-1',
        status=a2a_pb2.TaskStatus(state=a2a_pb2.TaskState.TASK_STATE_CANCELLED),
    )
    mock_grpc_stub.CancelTask.return_value = response_proto

    result = await grpc_client.cancel_task(request_params)

    mock_grpc_stub.CancelTask.assert_awaited_once_with(
        a2a_pb2.CancelTaskRequest(name='tasks/task-1')
    )
    assert isinstance(result, types.Task)
    assert result.status.state == types.TaskState.canceled


@pytest.mark.asyncio
async def test_set_task_callback(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test setting a task callback."""
    request_params = types.TaskPushNotificationConfig(
        taskId='task-1',
        pushNotificationConfig=types.PushNotificationConfig(
            url='http://callback.url'
        ),
    )
    response_proto = a2a_pb2.TaskPushNotificationConfig(
        name='tasks/task-1/pushNotifications/config-1',
        push_notification_config=a2a_pb2.PushNotificationConfig(
            url='http://callback.url'
        ),
    )
    mock_grpc_stub.CreateTaskPushNotification.return_value = response_proto

    result = await grpc_client.set_task_callback(request_params)

    mock_grpc_stub.CreateTaskPushNotification.assert_awaited_once()
    assert isinstance(result, types.TaskPushNotificationConfig)
    assert result.pushNotificationConfig.url == 'http://callback.url'


@pytest.mark.asyncio
async def test_get_task_callback(
    grpc_client: A2AGrpcClient, mock_grpc_stub: AsyncMock
):
    """Test getting a task callback."""
    request_params = types.TaskIdParams(id='task-1')
    response_proto = a2a_pb2.TaskPushNotificationConfig(
        name='tasks/task-1/pushNotifications/undefined',
        push_notification_config=a2a_pb2.PushNotificationConfig(
            url='http://callback.url'
        ),
    )
    mock_grpc_stub.GetTaskPushNotification.return_value = response_proto

    result = await grpc_client.get_task_callback(request_params)

    mock_grpc_stub.GetTaskPushNotification.assert_awaited_once_with(
        a2a_pb2.GetTaskPushNotificationRequest(
            name='tasks/task-1/pushNotifications/undefined'
        )
    )
    assert isinstance(result, types.TaskPushNotificationConfig)
    assert result.pushNotificationConfig.url == 'http://callback.url'
