import uuid

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
    """Helper class for publishing updates to a task."""

    def __init__(self, event_queue: EventQueue, task_id: str, context_id: str):
        self.event_queue = event_queue
        self.task_id = task_id
        self.context_id = context_id

    def update_status(
        self, state: TaskState, message: Message | None = None, final=False
    ):
        """Update the status of the task."""
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
        artifact_id=str(uuid.uuid4()),
        name: str | None = None,
    ):
        """Add an artifact to the task."""
        self.event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                taskId=self.task_id,
                contextId=self.context_id,
                artifact=Artifact(
                    artifactId=artifact_id,
                    name=name,
                    parts=parts,
                ),
            )
        )

    def complete(self, message: Message | None = None):
        """Mark the task as completed."""
        self.update_status(
            TaskState.completed,
            message=message,
            final=True,
        )

    def submit(self, message: Message | None = None):
        """Mark the task as submitted."""
        self.update_status(
            TaskState.submitted,
            message=message,
        )

    def start_work(self, message: Message | None = None):
        """Mark the task as working."""
        self.update_status(
            TaskState.working,
            message=message,
        )

    def new_agent_message(
        self, parts: list[Part], final=False, metadata=None
    ) -> Message:
        """Create a new message for the task."""
        return Message(
            role=Role.agent,
            taskId=self.task_id,
            contextId=self.context_id,
            messageId=str(uuid.uuid4()),
            metadata=metadata,
            final=final,
            parts=parts,
        )
