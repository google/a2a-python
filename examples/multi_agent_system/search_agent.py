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

import uuid # For generating unique IDs in the test block

# Core imports from the a2a framework
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.types import Message, Part, Role, TextPart # Core types
from a2a.utils.message import new_agent_text_message, get_message_text # Message utilities


class SearchAgent(AgentExecutor):
    """
    An agent that receives a search query and returns dummy search results.
    It uses the a2a.types.Message format.
    """

    def __init__(self, name: str = "SearchAgent"):
        super().__init__(name=name)

    async def execute(self, message: Message) -> Message:
        """
        Executes the search task.

        Args:
            message: A Message object, expected to contain text parts with the search query.

        Returns:
            A new Message object (from the agent) containing the dummy search results as text.
        """
        # Assuming search requests come from a USER role or another agent that has processed a plan.
        # For this example, we won't be too strict on message.role.
        
        search_query = get_message_text(message)

        if not search_query:
            # Return an error message if no text query could be extracted
            return new_agent_text_message(
                text="Error: SearchAgent received a message with no search query.",
                context_id=message.contextId,
                task_id=message.taskId,
            )

        # Create dummy search results.
        # In a real scenario, this would involve calling a search API or database.
        dummy_results = [
            f"https://example.com/search?q={search_query.replace(' ', '+')}&result=1",
            f"https://example.com/search?q={search_query.replace(' ', '+')}&result=2",
            f"https://en.wikipedia.org/wiki/{search_query.replace(' ', '_')}",
            f"Relevant internal document: DOC-{search_query.upper().replace(' ', '-')}-001",
        ]
        
        results_content = f"Search results for query: '{search_query}'\n" + "\n".join(dummy_results)

        # Create an agent message containing the search results
        response_message = new_agent_text_message(
            text=results_content,
            context_id=message.contextId, # Carry over context ID
            task_id=message.taskId,       # Carry over task ID
        )
        return response_message

    async def cancel(self, interaction_id: str) -> None:
        """
        Cancels an ongoing task.
        For SearchAgent, execute is quick. This fulfills the AgentExecutor interface.
        The interaction_id could correspond to a context_id or task_id.
        """
        print(f"Cancellation requested for interaction/context/task '{interaction_id}' in {self.name}.")
        # As execute() is not long-running, no specific cancellation logic is implemented.
        # In a real search agent that makes external API calls, this would involve
        # attempting to cancel the HTTP request or database query.
        # raise NotImplementedError("SearchAgent does not support explicit task cancellation yet.")
        pass # Acknowledging the request is sufficient for this simple agent.


if __name__ == "__main__":
    # Example of how to use the SearchAgent (for testing)
    
    # Mock AgentExecutor for the main() to be runnable if a2a is not fully set up
    class MockAgentExecutor:
        def __init__(self, name: str):
            self.name = name
        # async def cancel(self, interaction_id: str):
        #     pass

    original_agent_executor = AgentExecutor 
    AgentExecutor = MockAgentExecutor

    async def main_test():
        search_agent = SearchAgent()

        # Simulate an incoming user message with a search query
        user_search_query = "large language models applications"
        
        test_message = Message(
            role=Role.USER, # Or could be from another agent
            parts=[Part(root=TextPart(text=user_search_query))],
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()), # Task ID from the overall process
            contextId=str(uuid.uuid4()) # Context ID for the interaction
        )

        print(f"Sending query to SearchAgent: '{user_search_query}'")
        response_message = await search_agent.execute(test_message)

        print(f"\nSearch Agent Response (Role: {response_message.role}):")
        print(get_message_text(response_message))

        # Test cancel
        print(f"\nRequesting cancellation for contextId: {test_message.contextId}")
        await search_agent.cancel(test_message.contextId)

        # Test message with no query
        empty_message = Message(
            role=Role.USER,
            parts=[], 
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()),
            contextId=str(uuid.uuid4())
        )
        print(f"\nSending empty message to SearchAgent...")
        error_response = await search_agent.execute(empty_message)
        print(f"Search Agent Error Response:\n{get_message_text(error_response)}")

    import asyncio
    try:
        asyncio.run(main_test())
    finally:
        AgentExecutor = original_agent_executor # Restore original
        print("\nRestored AgentExecutor. SearchAgent example finished.")
