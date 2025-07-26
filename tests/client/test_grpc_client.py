from unittest.mock import AsyncMock, MagicMock

import grpc
import pytest

from a2a.client import A2AGrpcClient
from a2a.grpc import a2a_pb2, a2a_pb2_grpc
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    Artifact,
    Message,
    MessageSendParams,
    Part,
    PushNotificationAuthenticationInfo,
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
from a2a.utils.errors import ServerError


# Fixtures
@pytest.fixture
def mock_grpc_stub() -> AsyncMock:
    """Provides a mock gRPC stub with methods mocked."""
    stub = AsyncMock(spec=a2a_pb2_grpc.A2AServiceStub)
    stub.SendMessage = AsyncMock()
    stub.SendStreamingMessage = MagicMock()
    stub.GetTask = AsyncMock()
    stub.CancelTask = AsyncMock()
    stub.CreateTaskPushNotificationConfig = AsyncMock()
    stub.GetTaskPushNotificationConfig = AsyncMock()
    return stub


@pytest.fixture
def sample_agent_card() -> AgentCard:
    """Provides a minimal agent card for initialization."""
    return AgentCard(
        name='gRPC Test Agent',
        description='Agent for testing gRPC client',
        url='grpc://localhost:50051',
        version='1.0',
        capabilities=AgentCapabilities(streaming=True, push_notifications=True),
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
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
            message_id='msg-1',
            parts=[Part(root=TextPart(text='Hello'))],
        )
    )


@pytest.fixture
def sample_task() -> Task:
    """Provides a sample Task object."""
    return Task(
        id='task-1',
        context_id='ctx-1',
        status=TaskStatus(state=TaskState.completed),
    )


@pytest.fixture
def sample_message() -> Message:
    """Provides a sample Message object."""
    return Message(
        role=Role.agent,
        message_id='msg-response',
        parts=[Part(root=TextPart(text='Hi there'))],
    )


@pytest.fixture
def sample_artifact() -> Artifact:
    """Provides a sample Artifact object."""
    return Artifact(
        artifactId='artifact-1',
        name='example.txt',
        description='An example artifact',
        parts=[Part(root=TextPart(text='Hi there'))],
        metadata={},
        extensions=[],
    )


@pytest.fixture
def sample_task_status_update_event() -> TaskStatusUpdateEvent:
    """Provides a sample TaskStatusUpdateEvent."""
    return TaskStatusUpdateEvent(
        taskId='task-1',
        contextId='ctx-1',
        status=TaskStatus(state=TaskState.working),
        final=False,
        metadata={},
    )


@pytest.fixture
def sample_task_artifact_update_event(
    sample_artifact,
) -> TaskArtifactUpdateEvent:
    """Provides a sample TaskArtifactUpdateEvent."""
    return TaskArtifactUpdateEvent(
        taskId='task-1',
        contextId='ctx-1',
        artifact=sample_artifact,
        append=True,
        last_chunk=True,
        metadata={},
    )


@pytest.fixture
def sample_authentication_info() -> PushNotificationAuthenticationInfo:
    """Provides a sample AuthenticationInfo object."""
    return PushNotificationAuthenticationInfo(
        schemes=['apikey', 'oauth2'], credentials='secret-token'
    )


@pytest.fixture
def sample_push_notification_config(
    sample_authentication_info: PushNotificationAuthenticationInfo,
) -> PushNotificationConfig:
    """Provides a sample PushNotificationConfig object."""
    return PushNotificationConfig(
        id='config-1',
        url='https://example.com/notify',
        token='example-token',
        authentication=sample_authentication_info,
    )


@pytest.fixture
def sample_task_push_notification_config(
    sample_push_notification_config: PushNotificationConfig,
) -> TaskPushNotificationConfig:
    """Provides a sample TaskPushNotificationConfig object."""
    return TaskPushNotificationConfig(
        taskId='task-1',
        pushNotificationConfig=sample_push_notification_config,
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
    sample_message: Message,
    sample_task: Task,
    sample_task_status_update_event: TaskStatusUpdateEvent,
    sample_task_artifact_update_event: TaskArtifactUpdateEvent,
):
    """Test send_message_streaming that yields responses."""
    stream = MagicMock()
    stream.read = AsyncMock(
        side_effect=[
            a2a_pb2.StreamResponse(
                msg=proto_utils.ToProto.message(sample_message)
            ),
            a2a_pb2.StreamResponse(task=proto_utils.ToProto.task(sample_task)),
            a2a_pb2.StreamResponse(
                status_update=proto_utils.ToProto.task_status_update_event(
                    sample_task_status_update_event
                )
            ),
            a2a_pb2.StreamResponse(
                artifact_update=proto_utils.ToProto.task_artifact_update_event(
                    sample_task_artifact_update_event
                )
            ),
            grpc.aio.EOF,
        ]
    )
    mock_grpc_stub.SendStreamingMessage.return_value = stream

    responses = [
        response
        async for response in grpc_client.send_message_streaming(
            sample_message_send_params
        )
    ]

    mock_grpc_stub.SendStreamingMessage.assert_called_once()
    assert isinstance(responses[0], Message)
    assert responses[0].messageId == sample_message.messageId
    assert isinstance(responses[1], Task)
    assert responses[1].id == sample_task.id
    assert isinstance(responses[2], TaskStatusUpdateEvent)
    assert responses[2].taskId == sample_task_status_update_event.taskId
    assert isinstance(responses[3], TaskArtifactUpdateEvent)
    assert responses[3].taskId == sample_task_artifact_update_event.taskId


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
async def test_set_task_callback_with_valid_task(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_task_push_notification_config: TaskPushNotificationConfig,
):
    """Test setting a task push notification config with a valid task id."""
    task_id = 'task-1'
    config_id = 'config-1'
    mock_grpc_stub.CreateTaskPushNotificationConfig.return_value = (
        a2a_pb2.CreateTaskPushNotificationConfigRequest(
            parent=f'tasks/{task_id}',
            config_id=config_id,
            config=proto_utils.ToProto.task_push_notification_config(
                sample_task_push_notification_config
            ),
        )
    )

    response = await grpc_client.set_task_callback(
        sample_task_push_notification_config
    )

    mock_grpc_stub.CreateTaskPushNotificationConfig.assert_awaited_once_with(
        a2a_pb2.CreateTaskPushNotificationConfigRequest(
            config=proto_utils.ToProto.task_push_notification_config(
                sample_task_push_notification_config
            ),
        )
    )
    assert response.taskId == task_id


@pytest.mark.asyncio
async def test_set_task_callback_with_invalid_task(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_task_push_notification_config: TaskPushNotificationConfig,
):
    """Test setting a task push notification config with a invalid task id."""
    task_id = 'task-1'
    config_id = 'config-1'
    mock_grpc_stub.CreateTaskPushNotificationConfig.return_value = (
        a2a_pb2.CreateTaskPushNotificationConfigRequest(
            parent=f'invalid-path-to-tasks/{task_id}',
            config_id=config_id,
            config=proto_utils.ToProto.task_push_notification_config(
                sample_task_push_notification_config
            ),
        )
    )

    with pytest.raises(ServerError) as exc_info:
        await grpc_client.set_task_callback(
            sample_task_push_notification_config
        )
    assert 'No task for' in exc_info.value.error.message


@pytest.mark.asyncio
async def test_get_task_callback_with_valid_task(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_task_push_notification_config: TaskPushNotificationConfig,
):
    """Test retrieving a task push notification config with a valid task id."""
    task_id = 'task-1'
    config_id = 'config-1'
    mock_grpc_stub.GetTaskPushNotificationConfig.return_value = (
        a2a_pb2.CreateTaskPushNotificationConfigRequest(
            parent=f'tasks/{task_id}',
            config_id=config_id,
            config=proto_utils.ToProto.task_push_notification_config(
                sample_task_push_notification_config
            ),
        )
    )
    params = TaskIdParams(id=sample_task_push_notification_config.taskId)

    response = await grpc_client.get_task_callback(params)

    mock_grpc_stub.GetTaskPushNotificationConfig.assert_awaited_once_with(
        a2a_pb2.GetTaskPushNotificationConfigRequest(
            name=f'tasks/{params.id}/pushNotification/undefined',
        )
    )
    assert response.taskId == task_id


@pytest.mark.asyncio
async def test_get_task_callback_with_invalid_task(
    grpc_client: A2AGrpcClient,
    mock_grpc_stub: AsyncMock,
    sample_task_push_notification_config: TaskPushNotificationConfig,
):
    """Test retrieving a task push notification config with a invalid task id."""
    task_id = 'task-1'
    config_id = 'config-1'
    mock_grpc_stub.GetTaskPushNotificationConfig.return_value = (
        a2a_pb2.CreateTaskPushNotificationConfigRequest(
            parent=f'invalid-path-to-tasks/{task_id}',
            config_id=config_id,
            config=proto_utils.ToProto.task_push_notification_config(
                sample_task_push_notification_config
            ),
        )
    )
    params = TaskIdParams(id=sample_task_push_notification_config.taskId)

    with pytest.raises(ServerError) as exc_info:
        await grpc_client.get_task_callback(params)
    assert 'No task for' in exc_info.value.error.message
