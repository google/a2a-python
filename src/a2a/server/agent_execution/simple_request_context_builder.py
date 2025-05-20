import asyncio

from a2a.server.agent_execution import RequestContext, RequestContextBuilder
from a2a.server.tasks import TaskStore
from a2a.types import MessageSendParams, Task


class SimpleRequestContextBuilder(RequestContextBuilder):
    """Builds request context and populates referred tasks"""

    def __init__(
        self,
        should_populate_referred_tasks: bool = False,
        task_store: TaskStore | None = None,
    ) -> None:
        self._task_store = task_store
        self._should_populate_referred_tasks = should_populate_referred_tasks

    async def build(
        self,
        params: MessageSendParams | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        task: Task | None = None,
    ) -> RequestContext:
        related_tasks: list[Task] | None = None

        if (
            self._task_store
            and self._should_populate_referred_tasks
            and params
            and params.message.referenceTaskIds
        ):
            tasks = await asyncio.gather(
                *[
                    self._task_store.get(task_id)
                    for task_id in params.message.referenceTaskIds
                ]
            )
            related_tasks = [x for x in tasks if x is not None]

        return RequestContext(
            request=params,
            task_id=task_id,
            context_id=context_id,
            task=task,
            related_tasks=related_tasks,
        )
