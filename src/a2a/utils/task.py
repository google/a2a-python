import uuid

from a2a.types import Artifact, Message, Task, TaskState, TaskStatus


def new_task(request: Message) -> Task:
    return Task(
        status=TaskStatus(state=TaskState.submitted),
        id=(request.taskId if request.taskId else str(uuid.uuid4())),
        contextId=(
            request.contextId if request.contextId else str(uuid.uuid4())
        ),
        history=[request],
    )


def completed_task(
    task_id: str,
    context_id: str,
    artifacts: list[Artifact],
    history: list[Message] = [],
) -> Task:
    return Task(
        status=TaskStatus(state=TaskState.completed),
        id=task_id,
        contextId=context_id,
        artifacts=artifacts,
        history=history,
    )
