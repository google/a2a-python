import uuid

from unittest.mock import AsyncMock, patch

import pytest

from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
)


@pytest.fixture
def event_queue():
    """Create a mock event queue for testing."""
    return AsyncMock(spec=EventQueue)


@pytest.fixture
def task_updater(event_queue):
    """Create a TaskUpdater instance for testing."""
    return TaskUpdater(
        event_queue=event_queue,
        task_id='test-task-id',
        context_id='test-context-id',
    )


@pytest.fixture
def sample_message():
    """Create a sample message for testing."""
    return Message(
        role=Role.agent,
        taskId='test-task-id',
        contextId='test-context-id',
        messageId='test-message-id',
        parts=[Part(root=TextPart(text='Test message'))],
    )


@pytest.fixture
def sample_parts():
    """Create sample parts for testing."""
    return [Part(root=TextPart(text='Test part'))]


def test_init(event_queue):
    """Test that TaskUpdater initializes correctly."""
    task_updater = TaskUpdater(
        event_queue=event_queue,
        task_id='test-task-id',
        context_id='test-context-id',
    )

    assert task_updater.event_queue == event_queue
    assert task_updater.task_id == 'test-task-id'
    assert task_updater.context_id == 'test-context-id'


@pytest.mark.asyncio
async def test_update_status_without_message(task_updater, event_queue):
    """Test updating status without a message."""
    await task_updater.update_status(TaskState.working)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.taskId == 'test-task-id'
    assert event.contextId == 'test-context-id'
    assert event.final is False
    assert event.status.state == TaskState.working
    assert event.status.message is None


@pytest.mark.asyncio
async def test_update_status_with_message(
    task_updater, event_queue, sample_message
):
    """Test updating status with a message."""
    await task_updater.update_status(TaskState.working, message=sample_message)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.taskId == 'test-task-id'
    assert event.contextId == 'test-context-id'
    assert event.final is False
    assert event.status.state == TaskState.working
    assert event.status.message == sample_message


@pytest.mark.asyncio
async def test_update_status_final(task_updater, event_queue):
    """Test updating status with final=True."""
    await task_updater.update_status(TaskState.completed, final=True)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.final is True
    assert event.status.state == TaskState.completed


@pytest.mark.asyncio
async def test_add_artifact_with_custom_id_and_name(
    task_updater, event_queue, sample_parts
):
    """Test adding an artifact with a custom ID and name."""
    await task_updater.add_artifact(
        parts=sample_parts,
        artifact_id='custom-artifact-id',
        name='Custom Artifact',
    )

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskArtifactUpdateEvent)
    assert event.artifact.artifactId == 'custom-artifact-id'
    assert event.artifact.name == 'Custom Artifact'
    assert event.artifact.parts == sample_parts


@pytest.mark.asyncio
async def test_complete_without_message(task_updater, event_queue):
    """Test marking a task as completed without a message."""
    await task_updater.complete()

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.completed
    assert event.final is True
    assert event.status.message is None


@pytest.mark.asyncio
async def test_complete_with_message(task_updater, event_queue, sample_message):
    """Test marking a task as completed with a message."""
    await task_updater.complete(message=sample_message)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.completed
    assert event.final is True
    assert event.status.message == sample_message


@pytest.mark.asyncio
async def test_submit_without_message(task_updater, event_queue):
    """Test marking a task as submitted without a message."""
    await task_updater.submit()

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.submitted
    assert event.final is False
    assert event.status.message is None


@pytest.mark.asyncio
async def test_submit_with_message(task_updater, event_queue, sample_message):
    """Test marking a task as submitted with a message."""
    await task_updater.submit(message=sample_message)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.submitted
    assert event.final is False
    assert event.status.message == sample_message


@pytest.mark.asyncio
async def test_start_work_without_message(task_updater, event_queue):
    """Test marking a task as working without a message."""
    await task_updater.start_work()

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.working
    assert event.final is False
    assert event.status.message is None


@pytest.mark.asyncio
async def test_start_work_with_message(
    task_updater, event_queue, sample_message
):
    """Test marking a task as working with a message."""
    await task_updater.start_work(message=sample_message)

    event_queue.enqueue_event.assert_called_once()
    event = event_queue.enqueue_event.call_args[0][0]

    assert isinstance(event, TaskStatusUpdateEvent)
    assert event.status.state == TaskState.working
    assert event.final is False
    assert event.status.message == sample_message


def test_new_agent_message(task_updater, sample_parts):
    """Test creating a new agent message."""
    with patch(
        'uuid.uuid4',
        return_value=uuid.UUID('12345678-1234-5678-1234-567812345678'),
    ):
        message = task_updater.new_agent_message(parts=sample_parts)

    assert message.role == Role.agent
    assert message.taskId == 'test-task-id'
    assert message.contextId == 'test-context-id'
    assert message.messageId == '12345678-1234-5678-1234-567812345678'
    assert message.parts == sample_parts
    assert message.metadata is None


def test_new_agent_message_with_metadata(task_updater, sample_parts):
    """Test creating a new agent message with metadata and final=True."""
    metadata = {'key': 'value'}

    with patch(
        'uuid.uuid4',
        return_value=uuid.UUID('12345678-1234-5678-1234-567812345678'),
    ):
        message = task_updater.new_agent_message(
            parts=sample_parts, metadata=metadata
        )

    assert message.role == Role.agent
    assert message.taskId == 'test-task-id'
    assert message.contextId == 'test-context-id'
    assert message.messageId == '12345678-1234-5678-1234-567812345678'
    assert message.parts == sample_parts
    assert message.metadata == metadata
