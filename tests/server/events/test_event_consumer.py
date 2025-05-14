import asyncio

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from a2a.server.events.event_consumer import EventConsumer
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    A2AError,
    Artifact,
    InternalError,
    JSONRPCError,
    Message,
    Part,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from a2a.utils.errors import ServerError


MINIMAL_TASK: dict[str, Any] = {
    'id': '123',
    'contextId': 'session-xyz',
    'status': {'state': 'submitted'},
    'type': 'task',
}

MESSAGE_PAYLOAD: dict[str, Any] = {
    'role': 'agent',
    'parts': [{'text': 'test message'}],
    'messageId': '111',
}


@pytest.fixture
def mock_event_queue():
    return AsyncMock(spec=EventQueue)


@pytest.fixture
def event_consumer(mock_event_queue: EventQueue):
    return EventConsumer(queue=mock_event_queue)


@pytest.mark.asyncio
async def test_consume_one_task_event(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    task_event = Task(**MINIMAL_TASK)
    mock_event_queue.dequeue_event.return_value = task_event
    result = await event_consumer.consume_one()
    assert result == task_event
    mock_event_queue.task_done.assert_called_once()


@pytest.mark.asyncio
async def test_consume_one_message_event(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    message_event = Message(**MESSAGE_PAYLOAD)
    mock_event_queue.dequeue_event.return_value = message_event
    result = await event_consumer.consume_one()
    assert result == message_event
    mock_event_queue.task_done.assert_called_once()


@pytest.mark.asyncio
async def test_consume_one_a2a_error_event(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    error_event = A2AError(InternalError())
    mock_event_queue.dequeue_event.return_value = error_event
    result = await event_consumer.consume_one()
    assert result == error_event
    mock_event_queue.task_done.assert_called_once()


@pytest.mark.asyncio
async def test_consume_one_jsonrpc_error_event(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    error_event = JSONRPCError(code=123, message='Some Error')
    mock_event_queue.dequeue_event.return_value = error_event
    result = await event_consumer.consume_one()
    assert result == error_event
    mock_event_queue.task_done.assert_called_once()


@pytest.mark.asyncio
async def test_consume_one_queue_empty(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    mock_event_queue.dequeue_event.side_effect = asyncio.QueueEmpty
    try:
        result = await event_consumer.consume_one()
        assert result is not None
    except ServerError:
        pass
    mock_event_queue.task_done.assert_not_called()


@pytest.mark.asyncio
async def test_consume_all_multiple_events(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    events: list[Any] = [
        Task(**MINIMAL_TASK),
        TaskArtifactUpdateEvent(
            taskId='task_123',
            contextId='session-xyz',
            artifact=Artifact(
                artifactId='11', parts=[Part(TextPart(text='text'))]
            ),
        ),
        TaskStatusUpdateEvent(
            taskId='task_123',
            contextId='session-xyz',
            status=TaskStatus(state=TaskState.working),
            final=True,
        ),
    ]
    cursor = 0

    async def mock_dequeue() -> Any:
        nonlocal cursor
        if cursor < len(events):
            event = events[cursor]
            cursor += 1
            return event

    mock_event_queue.dequeue_event = mock_dequeue
    consumed_events: list[Any] = []
    async for event in event_consumer.consume_all():
        consumed_events.append(event)
    assert len(consumed_events) == 3
    assert consumed_events[0] == events[0]
    assert consumed_events[1] == events[1]
    assert consumed_events[2] == events[2]
    assert mock_event_queue.task_done.call_count == 3


@pytest.mark.asyncio
async def test_consume_until_message(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    events: list[Any] = [
        Task(**MINIMAL_TASK),
        TaskArtifactUpdateEvent(
            taskId='task_123',
            contextId='session-xyz',
            artifact=Artifact(
                artifactId='11', parts=[Part(TextPart(text='text'))]
            ),
        ),
        Message(**MESSAGE_PAYLOAD),
        TaskStatusUpdateEvent(
            taskId='task_123',
            contextId='session-xyz',
            status=TaskStatus(state=TaskState.working),
            final=True,
        ),
    ]
    cursor = 0

    async def mock_dequeue() -> Any:
        nonlocal cursor
        if cursor < len(events):
            event = events[cursor]
            cursor += 1
            return event

    mock_event_queue.dequeue_event = mock_dequeue
    consumed_events: list[Any] = []
    async for event in event_consumer.consume_all():
        consumed_events.append(event)
    assert len(consumed_events) == 3
    assert consumed_events[0] == events[0]
    assert consumed_events[1] == events[1]
    assert consumed_events[2] == events[2]
    assert mock_event_queue.task_done.call_count == 3


@pytest.mark.asyncio
async def test_consume_message_events(
    event_consumer: MagicMock,
    mock_event_queue: MagicMock,
):
    events = [
        Message(**MESSAGE_PAYLOAD),
        Message(**MESSAGE_PAYLOAD, final=True),
    ]
    cursor = 0

    async def mock_dequeue() -> Any:
        nonlocal cursor
        if cursor < len(events):
            event = events[cursor]
            cursor += 1
            return event

    mock_event_queue.dequeue_event = mock_dequeue
    consumed_events: list[Any] = []
    async for event in event_consumer.consume_all():
        consumed_events.append(event)
    # Upon first Message the stream is closed.
    assert len(consumed_events) == 1
    assert consumed_events[0] == events[0]
    assert mock_event_queue.task_done.call_count == 1
