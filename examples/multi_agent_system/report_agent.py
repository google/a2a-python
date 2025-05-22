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


class ReportAgent(AgentExecutor):
    """
    An agent that receives combined data (e.g., plan and search results)
    and generates a simple report.
    It uses the a2a.types.Message format.
    """

    def __init__(self, name: str = "ReportAgent"):
        super().__init__(name=name)

    async def execute(self, message: Message) -> Message:
        """
        Executes the report generation task.

        Args:
            message: A Message object, expected to contain text parts with the
                     combined plan and search results.

        Returns:
            A new Message object (from the agent) containing the generated report as text.
        """
        
        combined_input_text = get_message_text(message)

        if not combined_input_text:
            # Return an error message if no text input could be extracted
            return new_agent_text_message(
                text="Error: ReportAgent received a message with no content to report.",
                context_id=message.contextId,
                task_id=message.taskId,
            )

        # Generate a simple report.
        # In a real scenario, this might involve more sophisticated formatting,
        # summarization, or data extraction.
        report_content = f"--- Combined Report ---\n\n"
        report_content += "Processed Input:\n"
        report_content += "---------------------\n"
        report_content += combined_input_text
        report_content += "\n---------------------\n"
        report_content += "End of Report.\n"
        

        # Create an agent message containing the report
        response_message = new_agent_text_message(
            text=report_content,
            context_id=message.contextId, # Carry over context ID
            task_id=message.taskId,       # Carry over task ID
        )
        return response_message

    async def cancel(self, interaction_id: str) -> None:
        """
        Cancels an ongoing task.
        For ReportAgent, execute is quick. This fulfills the AgentExecutor interface.
        The interaction_id could correspond to a context_id or task_id.
        """
        print(f"Cancellation requested for interaction/context/task '{interaction_id}' in {self.name}.")
        # As execute() is not long-running, no specific cancellation logic is implemented.
        # raise NotImplementedError("ReportAgent does not support explicit task cancellation.")
        pass # Acknowledging the request is sufficient for this simple agent.


if __name__ == "__main__":
    # Example of how to use the ReportAgent (for testing)
    
    # Mock AgentExecutor for the main() to be runnable if a2a is not fully set up
    class MockAgentExecutor:
        def __init__(self, name: str):
            self.name = name
        # async def cancel(self, interaction_id: str):
        #     pass

    original_agent_executor = AgentExecutor 
    AgentExecutor = MockAgentExecutor

    async def main_test():
        report_agent = ReportAgent()

        # Simulate an incoming message with combined plan and search results
        simulated_plan = "Step 1: Query for X\nStep 2: Analyze Y"
        simulated_search_results = "Result 1 for X\nResult 2 for Y"
        combined_data = f"Plan:\n{simulated_plan}\n\nSearch Results:\n{simulated_search_results}"
        
        test_message = Message(
            role=Role.USER, # Or could be from another agent (e.g., HostAgent)
            parts=[Part(root=TextPart(text=combined_data))],
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()), 
            contextId=str(uuid.uuid4())
        )

        print(f"Sending data to ReportAgent:\n'{combined_data}'")
        response_message = await report_agent.execute(test_message)

        print(f"\nReport Agent Response (Role: {response_message.role}):")
        print(get_message_text(response_message))

        # Test cancel
        print(f"\nRequesting cancellation for contextId: {test_message.contextId}")
        await report_agent.cancel(test_message.contextId)

        # Test message with no content
        empty_message = Message(
            role=Role.USER,
            parts=[], 
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()),
            contextId=str(uuid.uuid4())
        )
        print(f"\nSending empty message to ReportAgent...")
        error_response = await report_agent.execute(empty_message)
        print(f"Report Agent Error Response:\n{get_message_text(error_response)}")

    import asyncio
    try:
        asyncio.run(main_test())
    finally:
        AgentExecutor = original_agent_executor # Restore original
        print("\nRestored AgentExecutor. ReportAgent example finished.")
