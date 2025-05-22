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

from examples.multi_agent_system.report_agent import ReportAgent
from a2a.types import Message, Role, TextPart, Part
from a2a.utils.message import get_message_text, new_user_text_message

@pytest.fixture
def report_agent_instance():
    """Provides an instance of ReportAgent."""
    return ReportAgent(name="TestReportAgent")

@pytest.fixture
def sample_combined_data():
    """Provides a sample combined data string (plan + search results)."""
    plan = "Plan:\nStep 1: Do this.\nStep 2: Do that."
    search_results = "Search Results:\nResult A found.\nResult B found."
    return f"{plan}\n\n{search_results}"

@pytest.fixture
def user_message_with_data(sample_combined_data):
    """Provides a sample user Message object with combined data."""
    return new_user_text_message(
        text=sample_combined_data,
        context_id=str(uuid.uuid4()),
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
async def test_report_agent_execute_success(report_agent_instance: ReportAgent, user_message_with_data: Message, sample_combined_data: str):
    """
    Tests successful report generation by the ReportAgent.
    """
    response_message = await report_agent_instance.execute(message=user_message_with_data)

    assert response_message is not None
    assert response_message.role == Role.AGENT
    assert response_message.contextId == user_message_with_data.contextId
    assert response_message.taskId == user_message_with_data.taskId

    response_text = get_message_text(response_message)
    assert "--- Combined Report ---" in response_text
    assert "Processed Input:" in response_text
    assert sample_combined_data in response_text # Original data should be part of the report
    assert "End of Report." in response_text
    assert not response_text.startswith("Error:")

@pytest.mark.asyncio
async def test_report_agent_execute_empty_data(report_agent_instance: ReportAgent, empty_user_message: Message):
    """
    Tests ReportAgent's response to empty input data.
    """
    response_message = await report_agent_instance.execute(message=empty_user_message)

    assert response_message is not None
    assert response_message.role == Role.AGENT # Still replies as an agent
    
    response_text = get_message_text(response_message)
    assert "Error: ReportAgent received a message with no content to report." in response_text

@pytest.mark.asyncio
async def test_report_agent_cancel_method(report_agent_instance: ReportAgent):
    """
    Tests the cancel method of the ReportAgent.
    The current implementation just prints and passes.
    """
    test_interaction_id = "test_cancel_interaction_report_789"
    try:
        await report_agent_instance.cancel(interaction_id=test_interaction_id)
    except Exception as e:
        pytest.fail(f"ReportAgent.cancel() raised an unexpected exception: {e}")
    # No specific assertion needed if it's just a print/pass.
    # If it were to raise NotImplementedError, the test would be:
    # with pytest.raises(NotImplementedError):
    #     await report_agent_instance.cancel(interaction_id=test_interaction_id)
