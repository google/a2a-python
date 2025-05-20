import asyncio
import logging

from a2a.types import (
    A2AError,
    JSONRPCError,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
from a2a.utils.telemetry import SpanKind, trace_class


logger = logging.getLogger(__name__)


Event = (
    Message
    | Task
    | TaskStatusUpdateEvent
    | TaskArtifactUpdateEvent
    | A2AError
    | JSONRPCError
)
"""Type alias for events that can be enqueued."""


@trace_class(kind=SpanKind.SERVER)
class EventQueue:
    """Event queue for A2A responses from agent.

    Acts as a buffer between the agent's asynchronous execution and the
    server's response handling (e.g., streaming via SSE). Supports tapping
    to create child queues that receive the same events.
    """

    def __init__(self) -> None:
        """Initializes the EventQueue."""
        self.queue: asyncio.Queue[Event] = asyncio.Queue()
        self._children: list[EventQueue] = []
        logger.debug('EventQueue initialized.')

    def enqueue_event(self, event: Event):
        """Enqueues an event to this queue and all its children.

        Args:
            event: The event object to enqueue.
        """
        logger.debug(f'Enqueuing event of type: {type(event)}')
        self.queue.put_nowait(event)
        for child in self._children:
            child.enqueue_event(event)

    async def dequeue_event(self, no_wait: bool = False) -> Event:
        """Dequeues an event from the queue.

        Args:
            no_wait: If True, retrieve an event immediately or raise `asyncio.QueueEmpty`.
                     If False (default), wait until an event is available.

        Returns:
            The next event from the queue.

        Raises:
            asyncio.QueueEmpty: If `no_wait` is True and the queue is empty.
            asyncio.QueueShutDown: If the queue has been closed and is empty.
        """
        if no_wait:
            logger.debug('Attempting to dequeue event (no_wait=True).')
            event = self.queue.get_nowait()
            logger.debug(
                f'Dequeued event (no_wait=True) of type: {type(event)}'
            )
            return event

        logger.debug('Attempting to dequeue event (waiting).')
        event = await self.queue.get()
        logger.debug(f'Dequeued event (waited) of type: {type(event)}')
        return event

    def task_done(self) -> None:
        """Signals that a formerly enqueued task is complete.

        Used in conjunction with `dequeue_event` to track processed items.
        """
        logger.debug('Marking task as done in EventQueue.')
        self.queue.task_done()

    def tap(self) -> 'EventQueue':
        """Taps the event queue to create a new child queue that receives all future events.

        Returns:
            A new `EventQueue` instance that will receive all events enqueued
            to this parent queue from this point forward.
        """
        logger.debug('Tapping EventQueue to create a child queue.')
        queue = EventQueue()
        self._children.append(queue)
        return queue

    def close(self):
        """Closes the queue for future push events.

        Once closed, `dequeue_event` will eventually raise `asyncio.QueueShutDown`
        when the queue is empty. Also closes all child queues.
        """
        logger.debug('Closing EventQueue.')
        self.queue.shutdown()
        for child in self._children:
            child.close()
