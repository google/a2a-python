import asyncio
import logging

from collections.abc import AsyncGenerator, AsyncIterator

from a2a.server.events import Event, EventConsumer
from a2a.server.tasks.task_manager import TaskManager
from a2a.types import Message, Task, TaskState, TaskStatusUpdateEvent


logger = logging.getLogger(__name__)


class ResultAggregator:
    """ResultAggregator is used to process the event streams from an AgentExecutor.

    There are three main ways to use the ResultAggregator:
    1) As part of a processing pipe. consume_and_emit will construct the updated
       task as the events arrive, and re-emit those events for another consumer
    2) As part of a blocking call. consume_all will process the entire stream and
       return the final Task or Message object
    3) As part of a push solution where the latest Task is emitted after processing an event.
       consume_and_emit_task will consume the Event stream, process the events to the current
       Task object and emit that Task object.
    """

    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self._message: Message | None = None

    @property
    async def current_result(self) -> Task | Message | None:
        if self._message:
            return self._message
        return await self.task_manager.get_task()

    async def consume_and_emit(
        self, consumer: EventConsumer
    ) -> AsyncGenerator[Event]:
        """Processes the event stream and emits the same event stream out."""
        async for event in consumer.consume_all():
            await self.task_manager.process(event)
            yield event

    async def consume_all(
        self, consumer: EventConsumer
    ) -> Task | Message | None:
        """Processes the entire event stream and returns the final result."""
        async for event in consumer.consume_all():
            if isinstance(event, Message):
                self._message = event
                return event
            await self.task_manager.process(event)
        return await self.task_manager.get_task()

    async def consume_and_break_on_interrupt(
        self, consumer: EventConsumer
    ) -> tuple[Task | Message | None, bool]:
        """Process the event stream until completion or an interruptable state is encountered."""
        event_stream = consumer.consume_all()
        interrupted = False
        async for event in event_stream:
            if isinstance(event, Message):
                self._message = event
                return event, False
            await self.task_manager.process(event)
            if (
                isinstance(event, Task | TaskStatusUpdateEvent)
                and event.status.state == TaskState.auth_required
            ):
                # auth-required is a special state: the message should be
                # escalated back to the caller, but the agent is expected to
                # continue producing events once the authorization is received
                # out-of-band. This is in contrast to input-required, where a
                # new request is expected in order for the agent to make progress,
                # so the agent should exit.
                logger.debug(
                    'Encountered an auth-required task: breaking synchronous message/send flow.'
                )
                # TODO: We should track all outstanding tasks to ensure they eventually complete.
                asyncio.create_task(self._continue_consuming(event_stream))
                interrupted = True
                break
        return await self.task_manager.get_task(), interrupted

    async def _continue_consuming(
        self, event_stream: AsyncIterator[Event]
    ) -> None:
        async for event in event_stream:
            await self.task_manager.process(event)
