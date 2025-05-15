import asyncio
import logging

from collections.abc import AsyncGenerator

from a2a.server.events.event_queue import Event, EventQueue
from a2a.types import (
    InternalError,
    Message,
    Task,
    TaskState,
    TaskStatusUpdateEvent,
)
from a2a.utils.errors import ServerError


logger = logging.getLogger(__name__)


class EventConsumer:
    """Consumer to read events from the agent event queue."""

    def __init__(self, queue: EventQueue):
        self.queue = queue
        self._timeout = 0.5
        self._exception: BaseException | None = None
        logger.debug('EventConsumer initialized')

    async def consume_one(self) -> Event:
        """Consume one event from the agent event queue."""
        logger.debug('Attempting to consume one event.')
        try:
            event = await self.queue.dequeue_event(no_wait=True)
        except asyncio.QueueEmpty as e:
            logger.warning('Event queue was empty in consume_one.')
            raise ServerError(
                InternalError(message='Agent did not return any response')
            ) from e

        logger.debug(f'Dequeued event of type: {type(event)} in consume_one.')

        self.queue.task_done()

        return event

    async def consume_all(self) -> AsyncGenerator[Event]:
        """Consume all the generated streaming events from the agent."""
        logger.debug('Starting to consume all events from the queue.')
        while True:
            if self._exception:
                raise self._exception
            try:
                # We use a timeout when waiting for an event from the queue.
                # This is required because it allows the loop to check if
                # `self._exception` has been set by the `agent_task_callback`.
                # Without the timeout, loop might hang indefinitely if no events are
                # enqueued by the agent and the agent simply threw an exception
                event = await asyncio.wait_for(
                    self.queue.dequeue_event(), timeout=self._timeout
                )
                logger.debug(
                    f'Dequeued event of type: {type(event)} in consume_all.'
                )
                yield event
                self.queue.task_done()
                logger.debug(
                    'Marked task as done in event queue in consume_all'
                )

                is_final_event = (
                    (isinstance(event, TaskStatusUpdateEvent) and event.final)
                    or isinstance(event, Message)
                    or (
                        isinstance(event, Task)
                        and event.status.state
                        in (
                            TaskState.completed,
                            TaskState.canceled,
                            TaskState.failed,
                        )
                    )
                )

                if is_final_event:
                    logger.debug('Stopping event consumption in consume_all.')
                    self.queue.close()
                    break
            except TimeoutError:
                # continue polling until there is a final event
                continue
            except asyncio.QueueShutDown:
                break

    def agent_task_callback(self, agent_task: asyncio.Task[None]):
        if agent_task.exception() is not None:
            self._exception = agent_task.exception()
