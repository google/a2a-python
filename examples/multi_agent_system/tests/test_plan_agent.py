# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
import uuid
from unittest.mock import Mock # Though not used for event_queue/context in execute directly

from examples.multi_agent_system.plan_agent import PlanAgent
from a2a.types import Message, Role, TextPart, Part
from a2a.utils.message import get_message_text, new_user_text_message

@pytest.fixture
def plan_agent_instance():
    """Provides an instance of PlanAgent."""
    return PlanAgent(name="TestPlanAgent")

@pytest.fixture
def sample_task_description():
    """Provides a sample task description string."""
    return "Develop a marketing strategy for a new product."

@pytest.fixture
def user_message_with_task(sample_task_description):
    """Provides a sample user Message object with a task description."""
    # Using new_user_text_message for convenience, though manual creation is also fine
    return new_user_text_message(
        text=sample_task_description,
        context_id=str(uuid.uuid4()), # Or task_id
        task_id=str(uuid.uuid4())
    )

@pytest.fixture
def empty_user_message():
    """Provides a user Message object with no text content."""
    return Message(
        messageId=str(uuid.uuid4()),
        role=Role.USER,
        parts=[], # No text parts
        contextId=str(uuid.uuid4()),
        taskId=str(uuid.uuid4())
    )

@pytest.mark.asyncio
async def test_plan_agent_execute_success(plan_agent_instance: PlanAgent, user_message_with_task: Message, sample_task_description: str):
    """
    Tests successful plan generation by the PlanAgent.
    """
    response_message = await plan_agent_instance.execute(message=user_message_with_task)

    assert response_message is not None
    assert response_message.role == Role.AGENT
    assert response_message.contextId == user_message_with_task.contextId
    assert response_message.taskId == user_message_with_task.taskId

    response_text = get_message_text(response_message)
    assert sample_task_description in response_text
    assert "Step 1: Understand the task" in response_text
    assert "Step 5: Output the plan." in response_text
    assert not response_text.startswith("Error:")

@pytest.mark.asyncio
async def test_plan_agent_execute_empty_task_description(plan_agent_instance: PlanAgent, empty_user_message: Message):
    """
    Tests PlanAgent's response to an empty task description.
    """
    response_message = await plan_agent_instance.execute(message=empty_user_message)

    assert response_message is not None
    assert response_message.role == Role.AGENT # It still replies as an agent
    
    response_text = get_message_text(response_message)
    assert "Error: PlanAgent received a message with no text content." in response_text

@pytest.mark.asyncio
async def test_plan_agent_execute_non_user_role_message(plan_agent_instance: PlanAgent, sample_task_description: str):
    """
    Tests PlanAgent's behavior when receiving a message from a non-USER role.
    The current implementation logs a warning but still processes the task.
    """
    agent_message_with_task = Message(
        messageId=str(uuid.uuid4()),
        role=Role.AGENT, # Message from another agent
        parts=[Part(root=TextPart(text=sample_task_description))],
        contextId=str(uuid.uuid4()),
        taskId=str(uuid.uuid4())
    )

    response_message = await plan_agent_instance.execute(message=agent_message_with_task)

    assert response_message is not None
    assert response_message.role == Role.AGENT
    response_text = get_message_text(response_message)
    assert sample_task_description in response_text # Should still process
    assert "Step 1: Understand the task" in response_text
    assert not response_text.startswith("Error:")


@pytest.mark.asyncio
async def test_plan_agent_cancel_method(plan_agent_instance: PlanAgent):
    """
    Tests the cancel method of the PlanAgent.
    The current implementation just prints and passes.
    """
    test_interaction_id = "test_cancel_interaction_123"
    try:
        await plan_agent_instance.cancel(interaction_id=test_interaction_id)
        # If it had super().cancel that could fail:
        # await super(PlanAgent, plan_agent_instance).cancel(interaction_id=test_interaction_id)
    except Exception as e:
        pytest.fail(f"PlanAgent.cancel() raised an unexpected exception: {e}")
    # No specific assertion needed if it's just a print/pass, other than it doesn't error.
    # If it were to raise NotImplementedError, the test would be:
    # with pytest.raises(NotImplementedError):
    #     await plan_agent_instance.cancel(interaction_id=test_interaction_id)

# Example of how one might mock if PlanAgent.execute *did* use event_queue:
# @pytest.mark.asyncio
# async def test_plan_agent_execute_with_mocked_event_queue(plan_agent_instance: PlanAgent, user_message_with_task: Message):
#     """
#     Example test if PlanAgent.execute directly used an event_queue.
#     THIS IS NOT HOW THE CURRENT PlanAgent WORKS.
#     """
#     mock_event_queue = Mock()
#     mock_context = Mock() # If context was also a direct argument
    
#     # Let's imagine PlanAgent was modified to take these:
#     # response_message = await plan_agent_instance.execute(
#     #     message=user_message_with_task,
#     #     event_queue=mock_event_queue, # Hypothetical argument
#     #     context=mock_context          # Hypothetical argument
#     # )
    
#     # If execute was supposed to enqueue its own result:
#     # mock_event_queue.enqueue_event.assert_called_once()
#     # called_event_message = mock_event_queue.enqueue_event.call_args[0][0] # Assuming event is the first arg
#     # assert called_event_message.role == Role.AGENT
#     # assert "Step 1: Understand the task" in get_message_text(called_event_message)
    
#     # This test is for illustration; the actual PlanAgent.execute returns a Message.
#     pass
