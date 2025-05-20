"""Utility functions for creating A2A Task objects."""

import uuid

from a2a.types import Artifact, Message, Task, TaskState, TaskStatus


def new_task(request: Message) -> Task:
    """Creates a new Task object from an initial user message.

    Generates task and context IDs if not provided in the message.

    Args:
        request: The initial `Message` object from the user.

    Returns:
        A new `Task` object initialized with 'submitted' status and the input message in history.
    """
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
    history: list[Message] | None = None,
) -> Task:
    """Creates a Task object in the 'completed' state.

    Useful for constructing a final Task representation when the agent
    finishes and produces artifacts.

    Args:
        task_id: The ID of the task.
        context_id: The context ID of the task.
        artifacts: A list of `Artifact` objects produced by the task.
        history: An optional list of `Message` objects representing the task history.

    Returns:
        A `Task` object with status set to 'completed'.
    """
    if history is None:
        history = []
    return Task(
        status=TaskStatus(state=TaskState.completed),
        id=task_id,
        contextId=context_id,
        artifacts=artifacts,
        history=history,
    )
