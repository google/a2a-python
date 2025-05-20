from typing import Any
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from a2a.utils.helpers import (
    create_task_obj,
    append_artifact_to_task,
    build_text_artifact,
    validate,
)
from a2a.types import (
    Artifact,
    MessageSendParams,
    Message,
    Task,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TextPart,
    Part,
)
from a2a.utils.errors import ServerError, UnsupportedOperationError

# --- Helper Data ---
TEXT_PART_DATA: dict[str, Any] = {'type': 'text', 'text': 'Hello'}

MINIMAL_MESSAGE_USER: dict[str, Any] = {
    'role': 'user',
    'parts': [TEXT_PART_DATA],
    'messageId': 'msg-123',
    'type': 'message',
}

MINIMAL_TASK_STATUS: dict[str, Any] = {'state': 'submitted'}

MINIMAL_TASK: dict[str, Any] = {
    'id': 'task-abc',
    'contextId': 'session-xyz',
    'status': MINIMAL_TASK_STATUS,
    'type': 'task',
}

# Test create_task_obj
def test_create_task_obj():
    message = Message(**MINIMAL_MESSAGE_USER)
    send_params = MessageSendParams(message=message)

    task = create_task_obj(send_params)
    assert task.id is not None
    assert task.contextId == message.contextId
    assert task.status.state == TaskState.submitted
    assert len(task.history) == 1
    assert task.history[0] == message


# Test append_artifact_to_task
def test_append_artifact_to_task():
     # Prepare base task   
    task = Task(**MINIMAL_TASK)
    assert task.id == 'task-abc'
    assert task.contextId == 'session-xyz'
    assert task.status.state == TaskState.submitted
    assert task.history is None
    assert task.artifacts is None
    assert task.metadata is None

    # Prepare appending artifact and event
    artifact_1 = Artifact(
        artifactId="artifact-123", parts=[Part(root=TextPart(text="Hello"))]
    )
    append_event_1 = TaskArtifactUpdateEvent(artifact=artifact_1, append=False, taskId="123", contextId="123")

    # Test adding a new artifact (not appending)
    append_artifact_to_task(task, append_event_1)
    assert len(task.artifacts) == 1
    assert task.artifacts[0].artifactId == "artifact-123"
    assert task.artifacts[0].name == None
    assert len(task.artifacts[0].parts) == 1
    assert task.artifacts[0].parts[0].root.text == "Hello"

    # Test replacing the artifact
    artifact_2 = Artifact(
        artifactId="artifact-123", name="updated name", parts=[Part(root=TextPart(text="Updated"))]
    )
    append_event_2 = TaskArtifactUpdateEvent(artifact=artifact_2, append=False, taskId="123", contextId="123")
    append_artifact_to_task(task, append_event_2)
    assert len(task.artifacts) == 1  # Should still have one artifact
    assert task.artifacts[0].artifactId == "artifact-123"
    assert task.artifacts[0].name == "updated name"
    assert len(task.artifacts[0].parts) == 1
    assert task.artifacts[0].parts[0].root.text == "Updated"

    # Test appending parts to an existing artifact
    artifact_with_parts = Artifact(
        artifactId="artifact-123", parts=[Part(root=TextPart(text="Part 2"))]
    )
    append_event_3 = TaskArtifactUpdateEvent(artifact=artifact_with_parts, append=True, taskId="123", contextId="123")
    append_artifact_to_task(task, append_event_3)
    assert len(task.artifacts[0].parts) == 2
    assert task.artifacts[0].parts[0].root.text == "Updated"
    assert task.artifacts[0].parts[1].root.text == "Part 2"

    # Test adding another new artifact
    another_artifact_with_parts = Artifact(
        artifactId="new_artifact", parts=[Part(root=TextPart(text="new artifact Part 1"))]
    )
    append_event_4 = TaskArtifactUpdateEvent(artifact=another_artifact_with_parts, append=False, taskId="123", contextId="123")
    append_artifact_to_task(task, append_event_4)
    assert len(task.artifacts) == 2
    assert task.artifacts[0].artifactId == "artifact-123"
    assert task.artifacts[1].artifactId == "new_artifact"
    assert len(task.artifacts[0].parts) == 2
    assert len(task.artifacts[1].parts) == 1

    # Test appending part to a task that does not have a matching artifact
    non_existing_artifact_with_parts = Artifact(
        artifactId="artifact-456", parts=[Part(root=TextPart(text="Part 1"))]
    )
    append_event_5 = TaskArtifactUpdateEvent(artifact=non_existing_artifact_with_parts, append=True, taskId="123", contextId="123")
    append_artifact_to_task(task, append_event_5)
    assert len(task.artifacts) == 2
    assert len(task.artifacts[0].parts) == 2
    assert len(task.artifacts[1].parts) == 1

# Test build_text_artifact
def test_build_text_artifact():
    artifact_id = "text_artifact"
    text = "This is a sample text"
    artifact = build_text_artifact(text, artifact_id)

    assert artifact.artifactId == artifact_id
    assert len(artifact.parts) == 1
    assert artifact.parts[0].root.text == text


# Test validate decorator
def test_validate_decorator():
    class TestClass:
        condition = True

        @validate(lambda self: self.condition, "Condition not met")
        def test_method(self):
            return "Success"

    obj = TestClass()

    # Test passing condition
    assert obj.test_method() == "Success"

    # Test failing condition
    obj.condition = False
    with pytest.raises(ServerError) as exc_info:
        obj.test_method()
    assert "Condition not met" in str(exc_info.value)
