from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import A2AError, UnsupportedOperationError


class BaseAgentExecutor(AgentExecutor):
    """Base AgentExecutor which returns unsupported operation error."""

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        event_queue.enqueue_event(A2AError(UnsupportedOperationError()))

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        event_queue.enqueue_event(A2AError(UnsupportedOperationError()))
