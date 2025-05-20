import uuid

from typing import Any

from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)


class TaskUpdater:
    """Helper class for agents to publish updates to a task's event queue.

    Simplifies the process of creating and enqueueing standard task events.
    """

    def __init__(self, event_queue: EventQueue, task_id: str, context_id: str):
        """Initializes the TaskUpdater.

        Args:
            event_queue: The `EventQueue` associated with the task.
            task_id: The ID of the task.
            context_id: The context ID of the task.
        """
        self.event_queue = event_queue
        self.task_id = task_id
        self.context_id = context_id

    def update_status(
        self, state: TaskState, message: Message | None = None, final=False
    ):
        """Updates the status of the task and publishes a `TaskStatusUpdateEvent`.

        Args:
            state: The new state of the task.
            message: An optional message associated with the status update.
            final: If True, indicates this is the final status update for the task.
        """
        self.event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                taskId=self.task_id,
                contextId=self.context_id,
                final=final,
                status=TaskStatus(
                    state=state,
                    message=message,
                ),
            )
        )

    def add_artifact(
        self,
        parts: list[Part],
        artifact_id: str = str(uuid.uuid4()),
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """Adds an artifact chunk to the task and publishes a `TaskArtifactUpdateEvent`.

        Args:
            parts: A list of `Part` objects forming the artifact chunk.
            artifact_id: The ID of the artifact. A new UUID is generated if not provided.
            name: Optional name for the artifact.
            metadata: Optional metadata for the artifact.
            append: Optional boolean indicating if this chunk appends to a previous one.
            last_chunk: Optional boolean indicating if this is the last chunk.
        """
        self.event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                taskId=self.task_id,
                contextId=self.context_id,
                artifact=Artifact(
                    artifactId=artifact_id,
                    name=name,
                    parts=parts,
                    metadata=metadata,
                ),
            )
        )

    def complete(self, message: Message | None = None):
        """Marks the task as completed and publishes a final status update."""
        self.update_status(
            TaskState.completed,
            message=message,
            final=True,
        )

    def failed(self, message: Message | None = None):
        """Marks the task as failed and publishes a final status update."""
        self.update_status(TaskState.failed, message=message, final=True)

    def submit(self, message: Message | None = None):
        """Marks the task as submitted and publishes a status update."""
        self.update_status(
            TaskState.submitted,
            message=message,
        )

    def start_work(self, message: Message | None = None):
        """Marks the task as working and publishes a status update."""
        self.update_status(
            TaskState.working,
            message=message,
        )

    def new_agent_message(
        self,
        parts: list[Part],
        metadata: dict[str, Any] | None = None,
    ) -> Message:
        """Creates a new message object sent by the agent for this task/context.

        Note: This method only *creates* the message object. It does not
              automatically enqueue it.

        Args:
            parts: A list of `Part` objects for the message content.
            final: Optional boolean indicating if this is the final message in a stream.
            metadata: Optional metadata for the message.

        Returns:
            A new `Message` object.
        """
        return Message(
            role=Role.agent,
            taskId=self.task_id,
            contextId=self.context_id,
            messageId=str(uuid.uuid4()),
            metadata=metadata,
            parts=parts,
        )
