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

import asyncio
import httpx
import uuid # For generating unique IDs in the test block

# Core imports from the a2a framework
from a2a.client.client import A2AClient, A2AClientTaskInfo
from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.types import Message, Part, Role, TextPart # Core types
from a2a.utils.message import new_agent_text_message, get_message_text, new_user_text_message # Message utilities


class HostAgent(AgentExecutor):
    """
    An agent that orchestrates calls to PlanAgent, SearchAgent, and ReportAgent
    to process a user's task.
    """

    def __init__(
        self,
        plan_agent_url: str,
        search_agent_url: str,
        report_agent_url: str,
        name: str = "HostAgent",
    ):
        super().__init__(name=name)
        self.plan_agent_url = plan_agent_url
        self.search_agent_url = search_agent_url
        self.report_agent_url = report_agent_url
        # A2AClients will be initialized within execute, along with httpx.AsyncClient

    async def _call_sub_agent(
        self,
        client: A2AClient,
        agent_name: str, # For logging/error messages
        input_text: str,
        original_message: Message, # To carry over contextId, taskId
    ) -> str:
        """Helper to call a sub-agent and extract its text response."""
        # Create a message to send to the sub-agent.
        # It's a "user" message from the perspective of the sub-agent.
        # However, the A2AClient might wrap this in a Task structure.
        # The A2AClient's execute_agent_task expects a list of Message objects as input.
        sub_agent_input_message = new_user_text_message( # HostAgent acts as a "user" to sub-agents
            text=input_text,
            context_id=original_message.contextId, # Propagate context
            task_id=original_message.taskId,       # Propagate task
        )

        try:
            # The A2AClient.execute_agent_task expects a list of Messages
            # and returns an A2AClientTaskInfo object.
            task_info: A2AClientTaskInfo = await client.execute_agent_task(
                messages=[sub_agent_input_message]
            )
            
            # The final message from the sub-agent is often in task_info.result.messages
            if task_info.result and task_info.result.messages:
                # Assuming the last message is the agent's response
                agent_response_message = task_info.result.messages[-1]
                if agent_response_message.role == Role.AGENT:
                    return get_message_text(agent_response_message)
                else:
                    return f"Error: {agent_name} did not respond with an AGENT message."
            else:
                return f"Error: No response messages from {agent_name}."

        except Exception as e:
            # Log the exception or handle it more gracefully
            print(f"Error calling {agent_name} at {client._server_url}: {e}")
            return f"Error: Could not get response from {agent_name} due to {type(e).__name__}."


    async def execute(self, message: Message) -> Message:
        """
        Orchestrates the sub-agents to process the task.
        """
        task_description = get_message_text(message)
        if not task_description:
            return new_agent_text_message(
                text="Error: HostAgent received a message with no task description.",
                context_id=message.contextId,
                task_id=message.taskId,
            )

        final_report = "Error: Orchestration failed." # Default error message

        async with httpx.AsyncClient() as http_client:
            plan_agent_client = A2AClient(server_url=self.plan_agent_url, http_client=http_client)
            search_agent_client = A2AClient(server_url=self.search_agent_url, http_client=http_client)
            report_agent_client = A2AClient(server_url=self.report_agent_url, http_client=http_client)

            # 1. Call PlanAgent
            plan = await self._call_sub_agent(
                plan_agent_client, "PlanAgent", task_description, message
            )
            if plan.startswith("Error:"):
                return new_agent_text_message(text=plan, context_id=message.contextId, task_id=message.taskId)

            # 2. Call SearchAgent
            # For simplicity, using the original task description as the search query.
            # A more advanced version might parse the plan to create specific queries.
            search_query = task_description 
            search_results = await self._call_sub_agent(
                search_agent_client, "SearchAgent", search_query, message
            )
            if search_results.startswith("Error:"):
                 # Proceed with reporting what we have, or return error
                combined_input_for_report = f"Plan:\n{plan}\n\nSearch Results: Failed - {search_results}"
            else:
                combined_input_for_report = f"Plan:\n{plan}\n\nSearch Results:\n{search_results}"

            # 3. Call ReportAgent
            final_report = await self._call_sub_agent(
                report_agent_client, "ReportAgent", combined_input_for_report, message
            )
            # If final_report itself is an error string from _call_sub_agent, it will be returned.

        # Return the final report from ReportAgent
        return new_agent_text_message(
            text=final_report,
            context_id=message.contextId,
            task_id=message.taskId,
        )

    async def cancel(self, interaction_id: str) -> None:
        """
        Cancels an ongoing task.
        For HostAgent, this would ideally involve propagating cancellations to sub-agents.
        """
        print(f"Cancellation requested for interaction/context/task '{interaction_id}' in {self.name}.")
        # TODO: Implement cancellation propagation to sub-agents if their A2AClient interface supports it.
        # For now, this is a placeholder.
        raise NotImplementedError(
            "HostAgent cancellation requires propagation to sub-agents, which is not yet implemented."
        )


if __name__ == "__main__":
    # This example is more complex to run directly as it involves HTTP calls
    # to other agents. For a simple test, we would mock A2AClient.

    # --- Mocking section ---
    class MockA2AClient:
        def __init__(self, server_url: str, http_client=None):
            self._server_url = server_url
            self.http_client = http_client # Keep httpx.AsyncClient for realism if used by HostAgent

        async def execute_agent_task(self, messages: list[Message]) -> A2AClientTaskInfo:
            input_text = get_message_text(messages[0])
            # Simulate responses based on the agent URL or input
            response_text = ""
            if "plan" in self._server_url:
                response_text = f"Plan for '{input_text}': Step 1, Step 2."
            elif "search" in self._server_url:
                response_text = f"Search results for '{input_text}': Result A, Result B."
            elif "report" in self._server_url:
                response_text = f"Report based on: {input_text}"
            
            # Simulate A2AClientTaskInfo structure
            response_message = new_agent_text_message(
                text=response_text,
                context_id=messages[0].contextId,
                task_id=messages[0].taskId
            )
            # Simplified TaskResult and A2AClientTaskInfo
            class MockTaskResult:
                def __init__(self, messages):
                    self.messages = messages
            class MockA2AClientTaskInfo(A2AClientTaskInfo):
                 def __init__(self, messages):
                    super().__init__(task_id="", status="", messages=messages, result=MockTaskResult(messages=messages))

            return MockA2AClientTaskInfo(messages=[response_message])

    # Store original and apply mock
    original_a2a_client = A2AClient
    A2AClient = MockA2AClient # type: ignore

    # Mock AgentExecutor for HostAgent itself
    class MockAgentExecutor:
        def __init__(self, name: str):
            self.name = name
    original_agent_executor = AgentExecutor
    AgentExecutor = MockAgentExecutor # type: ignore
    # --- End Mocking section ---

    async def main_test():
        # Dummy URLs for the mocked clients
        plan_url = "http://mockplanagent.test"
        search_url = "http://mocksearchagent.test"
        report_url = "http://mockreportagent.test"

        host_agent = HostAgent(
            plan_agent_url=plan_url,
            search_agent_url=search_url,
            report_agent_url=report_url,
        )

        user_task = "Research benefits of async programming and report them."
        test_message = new_user_text_message(
            text=user_task,
            context_id=str(uuid.uuid4()),
            task_id=str(uuid.uuid4())
        )

        print(f"HostAgent processing task: '{user_task}'")
        final_response = await host_agent.execute(test_message)
        
        print("\nHostAgent Final Response:")
        print(get_message_text(final_response))

        # Test cancellation (will raise NotImplementedError as per implementation)
        try:
            print("\nTesting HostAgent cancellation...")
            await host_agent.cancel(test_message.contextId)
        except NotImplementedError as e:
            print(f"Cancellation test: Caught expected error - {e}")

    try:
        asyncio.run(main_test())
    finally:
        # Restore original classes
        A2AClient = original_a2a_client # type: ignore
        AgentExecutor = original_agent_executor # type: ignore
        print("\nRestored A2AClient and AgentExecutor. HostAgent example finished.")
