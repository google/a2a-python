import time

import pytest

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    TaskState,
    TextPart,
)


class DummyAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        task_updater = TaskUpdater(
            event_queue, context.task_id, context.context_id
        )
        async for i in self._run():
            parts = [Part(root=TextPart(text=f'Event {i}'))]
            try:
                await task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(parts),
                )
            except RuntimeError:
                # Stop processing when the event loop is closed
                break

    async def _run(self):
        for i in range(1_000_000):  # Simulate a long-running stream
            yield i

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        pass


@pytest.mark.asyncio
async def test_on_message_send_stream():
    request_handler = DefaultRequestHandler(
        DummyAgentExecutor(), InMemoryTaskStore()
    )
    message_params = MessageSendParams(
        message=Message(
            role=Role.user,
            messageId='msg-123',
            parts=[Part(root=TextPart(text='How are you?'))],
        ),
    )

    async def consume_stream():
        events = []
        async for event in request_handler.on_message_send_stream(
            message_params
        ):
            events.append(event)
            if len(events) >= 3:
                break  # Stop after a few events

        return events

    # Consume first 3 events from the stream and measure time
    start = time.perf_counter()
    events = await consume_stream()
    elapsed = time.perf_counter() - start

    # Assert we received events quickly
    assert len(events) == 3
    assert elapsed < 0.5

    texts = [p.root.text for e in events for p in e.status.message.parts]
    assert texts == ['Event 0', 'Event 1', 'Event 2']
