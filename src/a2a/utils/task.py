import uuid

from a2a.types import Message, Task, TaskState, TaskStatus


def new_task(request: Message) -> Task:
    return Task(
        status=TaskStatus(state=TaskState.submitted),
        id=(request.taskId if request.taskId else str(uuid.uuid4())),
        contextId=(
            request.contextId if request.contextId else str(uuid.uuid4())
        ),
        history=[request],
    )
