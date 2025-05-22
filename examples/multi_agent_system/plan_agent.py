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

import uuid # For generating unique IDs if needed for context/task

# Corrected imports based on project structure
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.types import Message, Part, Role, TextPart # Core types
from a2a.utils.message import new_agent_text_message, get_message_text # Message utilities


class PlanAgent(AgentExecutor):
    """
    An agent that receives a task description and creates a plan.
    It uses the a2a.types.Message format.
    """

    def __init__(self, name: str = "PlanAgent"):
        super().__init__(name=name)

    async def execute(self, message: Message) -> Message:
        """
        Executes the planning task.

        Args:
            message: A Message object, expected to contain text parts with the task description.

        Returns:
            A new Message object (from the agent) containing the generated plan as text.
        """
        # Check if the message is from the user and contains text
        # (Simplified check: actual role check might be more complex depending on system design)
        if message.role != Role.USER: # Assuming plan requests come from USER role
             # Or handle messages from other agents if applicable
            print(f"Warning: {self.name} received a message not from USER role, but from {message.role}.")
            # Depending on strictness, could return an error message here.

        task_description = get_message_text(message)

        if not task_description:
            # Return an error message if no text could be extracted
            return new_agent_text_message(
                text="Error: PlanAgent received a message with no text content.",
                context_id=message.contextId,
                task_id=message.taskId,
            )

        # Create a simple plan.
        plan = [
            f"Step 1: Understand the task: '{task_description}'",
            "Step 2: Identify key components for the task.",
            "Step 3: Break down components into actionable steps.",
            "Step 4: Sequence the steps logically.",
            "Step 5: Output the plan.",
        ]
        plan_content = "\n".join(plan)

        # Create an agent message containing the plan
        # The new_agent_text_message sets role=Role.agent automatically.
        response_message = new_agent_text_message(
            text=plan_content,
            context_id=message.contextId, # Carry over context ID
            task_id=message.taskId,       # Carry over task ID
        )
        # Recipient is implicitly the system/user that sent the original message.
        return response_message

    async def cancel(self, interaction_id: str) -> None:
        """
        Cancels an ongoing task.
        For PlanAgent, execute is quick. This fulfills the AgentExecutor interface.
        The interaction_id could correspond to a context_id or task_id.
        """
        print(f"Cancellation requested for interaction/context/task '{interaction_id}' in {self.name}.")
        # In a real scenario, you might try to find tasks associated with interaction_id
        # and stop them if they are long-running.
        # For now, we'll consider it a successful no-op as the execute() is not long-running.
        # super().cancel() might not exist or have a different signature in the base AgentExecutor.
        # If the base class `AgentExecutor` from `a2a` has a specific `cancel` to be called:
        # await super().cancel(interaction_id)
        # For now, raising NotImplementedError if specific cancel logic is expected but not implemented.
        # However, a simple acknowledgment is also fine for simple agents.
        # Let's assume the base AgentExecutor doesn't have a cancel to be called or it's handled by the framework.
        pass # Or raise NotImplementedError("PlanAgent does not support explicit task cancellation.")


if __name__ == "__main__":
    # Example of how to use the PlanAgent (for testing)
    # This requires the a2a types and utils to be available in PYTHONPATH.
    # Also, the AgentExecutor base class needs to be correctly defined.

    # Mock necessary parts of a2a for the main() to be runnable if a2a is not fully set up
    # This is a simplified mock for local testing of this file only.
    class MockAgentExecutor:
        def __init__(self, name: str):
            self.name = name
        # async def cancel(self, interaction_id: str): # Base cancel, if any
        #     print(f"MockAgentExecutor: Cancel called for {interaction_id}")
        #     pass

    # Replace the actual AgentExecutor with the mock for this test script
    # This is a common technique for unit testing or examples when the full environment isn't available.
    # However, this means we are not testing the *actual* base class behavior here.
    # For true integration, the script should run within the project's environment.

    # To make this example runnable without modifying the original AgentExecutor line:
    # We would need to ensure a2a.server.agent_execution.agent_executor.AgentExecutor is mockable
    # or the PYTHONPATH is set up. For now, let's assume the imports work.
    # If not, one would typically run this via a test runner that handles paths.

    original_agent_executor = AgentExecutor # Save original
    AgentExecutor = MockAgentExecutor # Replace with mock for this test block

    async def main_test():
        plan_agent = PlanAgent()

        # Simulate an incoming user message
        user_task_description = "Develop a new feature for the user authentication module."
        # Create a Message object similar to how the system might provide it
        # (messageId, taskId, contextId would usually be generated by the system)
        test_message = Message(
            role=Role.USER, # Message from the user
            parts=[Part(root=TextPart(text=user_task_description))],
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()),
            contextId=str(uuid.uuid4())
        )

        print(f"Sending task to PlanAgent: '{user_task_description}'")
        response_message = await plan_agent.execute(test_message)

        print(f"\nPlan Agent Response (Role: {response_message.role}):")
        print(get_message_text(response_message))

        # Test cancel
        print(f"\nRequesting cancellation for contextId: {test_message.contextId}")
        await plan_agent.cancel(test_message.contextId)

        # Test message with no text
        empty_message = Message(
            role=Role.USER,
            parts=[], # No parts, or non-TextPart parts
            messageId=str(uuid.uuid4()),
            taskId=str(uuid.uuid4()),
            contextId=str(uuid.uuid4())
        )
        print(f"\nSending empty message to PlanAgent...")
        error_response = await plan_agent.execute(empty_message)
        print(f"Plan Agent Error Response:\n{get_message_text(error_response)}")


    import asyncio
    try:
        asyncio.run(main_test())
    finally:
        AgentExecutor = original_agent_executor # Restore original
        print("\nRestored AgentExecutor. Example finished.")
