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
import pytest_asyncio # For async fixtures if needed, though not strictly here
import uuid
from unittest.mock import AsyncMock, patch, MagicMock, call

from examples.multi_agent_system.host_agent import HostAgent
from a2a.client.client import A2AClient, A2AClientTaskInfo
from a2a.types import Message, Role, TextPart, Part, TaskResult, TaskStatus
from a2a.utils.message import get_message_text, new_user_text_message, new_agent_text_message

DUMMY_PLAN_URL = "http://plan.test"
DUMMY_SEARCH_URL = "http://search.test"
DUMMY_REPORT_URL = "http://report.test"

@pytest.fixture
def host_agent_instance():
    """Provides an instance of HostAgent with dummy URLs."""
    return HostAgent(
        plan_agent_url=DUMMY_PLAN_URL,
        search_agent_url=DUMMY_SEARCH_URL,
        report_agent_url=DUMMY_REPORT_URL,
        name="TestHostAgent"
    )

@pytest.fixture
def sample_task_description():
    return "Test task: orchestrate sub-agents"

@pytest.fixture
def sample_user_message(sample_task_description):
    """Provides a sample user Message object for HostAgent input."""
    return new_user_text_message(
        text=sample_task_description,
        context_id=str(uuid.uuid4()),
        task_id=str(uuid.uuid4())
    )

@pytest.fixture
def empty_user_message():
    """Provides a user Message object with no text content."""
    return new_user_text_message(text="", context_id=str(uuid.uuid4()), task_id=str(uuid.uuid4()))


def create_mock_a2a_client_task_info(text_response: str, original_message: Message) -> A2AClientTaskInfo:
    """Helper to create a mock A2AClientTaskInfo object."""
    agent_reply_message = new_agent_text_message(
        text=text_response,
        context_id=original_message.contextId,
        task_id=original_message.taskId
    )
    # Create a TaskResult object that A2AClientTaskInfo expects
    task_result = TaskResult(
        task_id=original_message.taskId or str(uuid.uuid4()), # Ensure task_id is not None
        status=TaskStatus.COMPLETED, 
        messages=[agent_reply_message] # List of messages, last one is typically the result
    )
    return A2AClientTaskInfo(
        task_id=original_message.taskId or str(uuid.uuid4()),
        status=TaskStatus.COMPLETED, # Simplified status
        messages=[agent_reply_message], # Full message history for the task
        result=task_result # The final result object
    )


@pytest.mark.asyncio
@patch('examples.multi_agent_system.host_agent.A2AClient') # Patch A2AClient where it's used
async def test_host_agent_execute_success(
    MockA2AClientConstructor: MagicMock, 
    host_agent_instance: HostAgent, 
    sample_user_message: Message,
    sample_task_description: str
):
    # Create AsyncMock instances for each sub-agent client's execute_agent_task method
    mock_plan_client = AsyncMock(spec=A2AClient)
    mock_search_client = AsyncMock(spec=A2AClient)
    mock_report_client = AsyncMock(spec=A2AClient)

    # Configure the constructor mock to return different client mocks based on URL
    def side_effect_constructor(server_url, http_client):
        if server_url == DUMMY_PLAN_URL:
            return mock_plan_client
        elif server_url == DUMMY_SEARCH_URL:
            return mock_search_client
        elif server_url == DUMMY_REPORT_URL:
            return mock_report_client
        raise ValueError(f"Unexpected server_url: {server_url}")

    MockA2AClientConstructor.side_effect = side_effect_constructor
    
    # Define responses from sub-agents
    plan_response_text = f"Plan for '{sample_task_description}'"
    search_response_text = f"Search results for '{sample_task_description}'"
    report_response_text = f"Final report based on Plan and Search"

    mock_plan_client.execute_agent_task = AsyncMock(
        return_value=create_mock_a2a_client_task_info(plan_response_text, sample_user_message)
    )
    mock_search_client.execute_agent_task = AsyncMock(
        return_value=create_mock_a2a_client_task_info(search_response_text, sample_user_message)
    )
    mock_report_client.execute_agent_task = AsyncMock(
        return_value=create_mock_a2a_client_task_info(report_response_text, sample_user_message)
    )

    # Execute HostAgent
    final_message = await host_agent_instance.execute(message=sample_user_message)

    # Assertions
    MockA2AClientConstructor.assert_any_call(server_url=DUMMY_PLAN_URL, http_client=unittest.mock.ANY)
    MockA2AClientConstructor.assert_any_call(server_url=DUMMY_SEARCH_URL, http_client=unittest.mock.ANY)
    MockA2AClientConstructor.assert_any_call(server_url=DUMMY_REPORT_URL, http_client=unittest.mock.ANY)
    
    mock_plan_client.execute_agent_task.assert_called_once()
    # Check the content of the message sent to plan_agent
    plan_call_args = mock_plan_client.execute_agent_task.call_args[0][0] # messages list
    assert get_message_text(plan_call_args[0]) == sample_task_description

    mock_search_client.execute_agent_task.assert_called_once()
    search_call_args = mock_search_client.execute_agent_task.call_args[0][0]
    assert get_message_text(search_call_args[0]) == sample_task_description # Simple pass-through for query

    mock_report_client.execute_agent_task.assert_called_once()
    report_call_args = mock_report_client.execute_agent_task.call_args[0][0]
    expected_report_input = f"Plan:\n{plan_response_text}\n\nSearch Results:\n{search_response_text}"
    assert get_message_text(report_call_args[0]) == expected_report_input
    
    assert final_message.role == Role.AGENT
    assert get_message_text(final_message) == report_response_text
    assert final_message.contextId == sample_user_message.contextId
    assert final_message.taskId == sample_user_message.taskId


@pytest.mark.asyncio
@patch('examples.multi_agent_system.host_agent.A2AClient')
async def test_host_agent_execute_plan_agent_error(
    MockA2AClientConstructor: MagicMock, 
    host_agent_instance: HostAgent, 
    sample_user_message: Message
):
    mock_plan_client = AsyncMock(spec=A2AClient)
    # Other clients won't be called if plan fails early
    mock_search_client = AsyncMock(spec=A2AClient) 
    mock_report_client = AsyncMock(spec=A2AClient)

    def side_effect_constructor(server_url, http_client):
        if server_url == DUMMY_PLAN_URL: return mock_plan_client
        if server_url == DUMMY_SEARCH_URL: return mock_search_client # Should not be constructed
        if server_url == DUMMY_REPORT_URL: return mock_report_client # Should not be constructed
        raise ValueError(f"Unexpected server_url: {server_url}")
    MockA2AClientConstructor.side_effect = side_effect_constructor
    
    error_response_text = "Error: PlanAgent failed spectacularly."
    mock_plan_client.execute_agent_task = AsyncMock(
        # Simulate an error message being returned by _call_sub_agent
        return_value=create_mock_a2a_client_task_info(error_response_text, sample_user_message) 
    )
    # Hack: Modify the response text from create_mock_a2a_client_task_info to ensure it starts with "Error:"
    # for the HostAgent's internal check `if plan.startswith("Error:")`
    # This is a bit brittle. A better mock for _call_sub_agent would be ideal but is more complex.
    # For now, we make sure the text inside the message starts with "Error:"
    error_task_info = create_mock_a2a_client_task_info(error_response_text, sample_user_message)
    error_task_info.result.messages[0].parts[0].root.text = error_response_text 
    mock_plan_client.execute_agent_task.return_value = error_task_info


    final_message = await host_agent_instance.execute(message=sample_user_message)
    
    mock_plan_client.execute_agent_task.assert_called_once()
    mock_search_client.execute_agent_task.assert_not_called() # Should not be called
    mock_report_client.execute_agent_task.assert_not_called() # Should not be called
    
    assert final_message.role == Role.AGENT
    assert get_message_text(final_message) == error_response_text


@pytest.mark.asyncio
@patch('examples.multi_agent_system.host_agent.A2AClient')
async def test_host_agent_execute_search_agent_error(
    MockA2AClientConstructor: MagicMock,
    host_agent_instance: HostAgent,
    sample_user_message: Message,
    sample_task_description: str
):
    mock_plan_client = AsyncMock(spec=A2AClient)
    mock_search_client = AsyncMock(spec=A2AClient)
    mock_report_client = AsyncMock(spec=A2AClient)

    MockA2AClientConstructor.side_effect = lambda server_url, http_client: {
        DUMMY_PLAN_URL: mock_plan_client,
        DUMMY_SEARCH_URL: mock_search_client,
        DUMMY_REPORT_URL: mock_report_client
    }.get(server_url)

    plan_response_text = f"Plan for '{sample_task_description}'"
    search_error_text = "Error: SearchAgent could not find anything."
    report_response_text = "Final report reflecting search failure"

    mock_plan_client.execute_agent_task = AsyncMock(return_value=create_mock_a2a_client_task_info(plan_response_text, sample_user_message))
    
    search_error_task_info = create_mock_a2a_client_task_info(search_error_text, sample_user_message)
    search_error_task_info.result.messages[0].parts[0].root.text = search_error_text # Ensure it starts with "Error:"
    mock_search_client.execute_agent_task = AsyncMock(return_value=search_error_task_info)
    
    mock_report_client.execute_agent_task = AsyncMock(return_value=create_mock_a2a_client_task_info(report_response_text, sample_user_message))

    final_message = await host_agent_instance.execute(message=sample_user_message)

    mock_plan_client.execute_agent_task.assert_called_once()
    mock_search_client.execute_agent_task.assert_called_once()
    mock_report_client.execute_agent_task.assert_called_once()

    # Check that ReportAgent received input indicating search failure
    report_call_args = mock_report_client.execute_agent_task.call_args[0][0]
    expected_report_input = f"Plan:\n{plan_response_text}\n\nSearch Results: Failed - {search_error_text}"
    assert get_message_text(report_call_args[0]) == expected_report_input
    
    assert get_message_text(final_message) == report_response_text


@pytest.mark.asyncio
async def test_host_agent_execute_empty_task_description(host_agent_instance: HostAgent, empty_user_message: Message):
    """
    Tests HostAgent's response to an empty task description.
    """
    # No mocking needed for A2AClient as it should return error before client calls
    response_message = await host_agent_instance.execute(message=empty_user_message)

    assert response_message is not None
    assert response_message.role == Role.AGENT
    response_text = get_message_text(response_message)
    assert "Error: HostAgent received a message with no task description." in response_text


@pytest.mark.asyncio
async def test_host_agent_cancel_method(host_agent_instance: HostAgent):
    """
    Tests the cancel method of the HostAgent.
    Current implementation raises NotImplementedError.
    """
    test_interaction_id = "test_cancel_host_interaction_123"
    with pytest.raises(NotImplementedError) as excinfo:
        await host_agent_instance.cancel(interaction_id=test_interaction_id)
    assert "HostAgent cancellation requires propagation to sub-agents" in str(excinfo.value)
