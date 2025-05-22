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

from examples.multi_agent_system.search_agent import SearchAgent
from a2a.types import Message, Role, TextPart, Part
from a2a.utils.message import get_message_text, new_user_text_message

@pytest.fixture
def search_agent_instance():
    """Provides an instance of SearchAgent."""
    return SearchAgent(name="TestSearchAgent")

@pytest.fixture
def sample_search_query():
    """Provides a sample search query string."""
    return "latest advancements in AI"

@pytest.fixture
def user_message_with_query(sample_search_query):
    """Provides a sample user Message object with a search query."""
    return new_user_text_message(
        text=sample_search_query,
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
async def test_search_agent_execute_success(search_agent_instance: SearchAgent, user_message_with_query: Message, sample_search_query: str):
    """
    Tests successful search operation by the SearchAgent.
    """
    response_message = await search_agent_instance.execute(message=user_message_with_query)

    assert response_message is not None
    assert response_message.role == Role.AGENT
    assert response_message.contextId == user_message_with_query.contextId
    assert response_message.taskId == user_message_with_query.taskId

    response_text = get_message_text(response_message)
    assert f"Search results for query: '{sample_search_query}'" in response_text
    # Check for dummy result structure (e.g., contains "https://example.com")
    assert "https://example.com/search?q=" in response_text
    assert "https://en.wikipedia.org/wiki/" in response_text
    assert not response_text.startswith("Error:")

@pytest.mark.asyncio
async def test_search_agent_execute_empty_query(search_agent_instance: SearchAgent, empty_user_message: Message):
    """
    Tests SearchAgent's response to an empty search query.
    """
    response_message = await search_agent_instance.execute(message=empty_user_message)

    assert response_message is not None
    assert response_message.role == Role.AGENT # Still replies as an agent
    
    response_text = get_message_text(response_message)
    assert "Error: SearchAgent received a message with no search query." in response_text

@pytest.mark.asyncio
async def test_search_agent_cancel_method(search_agent_instance: SearchAgent):
    """
    Tests the cancel method of the SearchAgent.
    The current implementation just prints and passes.
    """
    test_interaction_id = "test_cancel_interaction_search_456"
    try:
        await search_agent_instance.cancel(interaction_id=test_interaction_id)
    except Exception as e:
        pytest.fail(f"SearchAgent.cancel() raised an unexpected exception: {e}")
    # No specific assertion needed if it's just a print/pass.
    # If it were to raise NotImplementedError, the test would be:
    # with pytest.raises(NotImplementedError):
    #     await search_agent_instance.cancel(interaction_id=test_interaction_id)
