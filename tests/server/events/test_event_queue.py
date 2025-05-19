import asyncio
import pytest
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    A2AError,
    JSONRPCError,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
    Artifact,
    Part,
    TextPart,
    TaskNotFoundError,
)
from typing import Any

MINIMAL_TASK: dict[str, Any] = {
    'id': '123',
    'contextId': 'session-xyz',
    'status': {'state': 'submitted'},
    'kind': 'task',
}
MESSAGE_PAYLOAD: dict[str, Any] = {
    'role': 'agent',
    'parts': [{'text': 'test message'}],
    'messageId': '111',
}


@pytest.fixture
def event_queue() -> EventQueue:
    return EventQueue()


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_event(event_queue: EventQueue) -> None:
    """Test that an event can be enqueued and dequeued."""
    event = Message(**MESSAGE_PAYLOAD)
    event_queue.enqueue_event(event)
    dequeued_event = await event_queue.dequeue_event()
    assert dequeued_event == event


@pytest.mark.asyncio
async def test_dequeue_event_no_wait(event_queue: EventQueue) -> None:
    """Test dequeue_event with no_wait=True."""
    event = Task(**MINIMAL_TASK)
    event_queue.enqueue_event(event)
    dequeued_event = await event_queue.dequeue_event(no_wait=True)
    assert dequeued_event == event


@pytest.mark.asyncio
async def test_dequeue_event_empty_queue_no_wait(
    event_queue: EventQueue,
) -> None:
    """Test dequeue_event with no_wait=True when the queue is empty."""
    with pytest.raises(asyncio.QueueEmpty):
        await event_queue.dequeue_event(no_wait=True)


@pytest.mark.asyncio
async def test_dequeue_event_wait(event_queue: EventQueue) -> None:
    """Test dequeue_event with the default wait behavior."""
    event = TaskStatusUpdateEvent(
        taskId='task_123',
        contextId='session-xyz',
        status=TaskStatus(state=TaskState.working),
        final=True,
    )
    event_queue.enqueue_event(event)
    dequeued_event = await event_queue.dequeue_event()
    assert dequeued_event == event


@pytest.mark.asyncio
async def test_task_done(event_queue: EventQueue) -> None:
    """Test the task_done method."""
    event = TaskArtifactUpdateEvent(
        taskId='task_123',
        contextId='session-xyz',
        artifact=Artifact(artifactId='11', parts=[Part(TextPart(text='text'))]),
    )
    event_queue.enqueue_event(event)
    _ = await event_queue.dequeue_event()
    event_queue.task_done()


@pytest.mark.asyncio
async def test_enqueue_different_event_types(
    event_queue: EventQueue,
) -> None:
    """Test enqueuing different types of events."""
    events: list[Any] = [
        A2AError(TaskNotFoundError()),
        JSONRPCError(code=111, message='rpc error'),
    ]
    for event in events:
        event_queue.enqueue_event(event)
        dequeued_event = await event_queue.dequeue_event()
        assert dequeued_event == event
