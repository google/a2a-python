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
import uuid

from a2a.client.client import A2AClient
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
    SendMessageResponse, # Correct response type for client.send_message
)
from a2a.utils.message import get_message_text # Helper to extract text

# Configuration
HOST_AGENT_BASE_URL = "http://localhost:8000" # Assuming HostAgent runs on port 8000
HOST_AGENT_CARD_URL = f"{HOST_AGENT_BASE_URL}/agent_card" # Default endpoint for agent card

async def main():
    """
    Client script to interact with the HostAgent.
    """
    print(f"Attempting to connect to HostAgent via card URL: {HOST_AGENT_CARD_URL}")

    try:
        async with httpx.AsyncClient() as http_client:
            # Get an A2AClient instance for the HostAgent using its agent card URL
            # This client will be configured to interact with the HostAgent's skills
            try:
                client: A2AClient = await A2AClient.get_client_from_agent_card_url(
                    agent_card_url=HOST_AGENT_CARD_URL, http_client=http_client
                )
                print(f"Successfully created A2AClient for HostAgent: {client.agent_id}")
            except Exception as e:
                print(f"Error creating A2AClient from agent card: {e}")
                print("Please ensure the HostAgent server is running and accessible.")
                return

            # Define the task for the HostAgent
            task_description = "Plan a two-day trip to Paris, including museum visits and local dining."
            print(f"\nSending task to HostAgent: '{task_description}'")

            # Create the message to send
            # For send_message, a context_id (or task_id) is usually required if the interaction
            # is not the very first one. If get_client_from_agent_card_url or the first send_message
            # doesn't establish a context, this might need adjustment (e.g., using start_task).
            # For this example, we'll assume send_message can initiate if no context_id is provided,
            # or that the client handles it for the primary skill.
            
            # A task_id is required by DefaultRequestHandler to create/lookup a task.
            # Let's generate one for this new interaction.
            # The `context_id` in `MessageSendParams` is often the same as `task_id` for the first message.
            current_task_id = str(uuid.uuid4())
            
            user_message = Message(
                messageId=str(uuid.uuid4()),
                role=Role.USER,
                parts=[Part(root=TextPart(text=task_description))],
                # taskId and contextId within the Message object itself are optional here,
                # as they are primarily for server-side tracking within a Task.
                # The crucial part is setting them in MessageSendParams for the request.
            )

            # Create MessageSendParams
            # The context_id here refers to the ongoing conversation/task context.
            # If this is the first message of a new task, this context_id will be used to create that task.
            message_params = MessageSendParams(
                message=user_message,
                # context_id=current_task_id, # DefaultRequestHandler uses task_id
                task_id=current_task_id # This is what DefaultRequestHandler will use to create a new task
            )

            # Create SendMessageRequest
            send_request = SendMessageRequest(params=message_params)

            try:
                # Call client.send_message()
                # This will typically send the message to the agent's default skill
                # or a skill determined by the client/server if context is ambiguous.
                # The DefaultRequestHandler on the server should pick this up,
                # create a new task using current_task_id, and pass it to HostAgent.execute().
                print(f"Sending message with task_id: {current_task_id}...")
                response: SendMessageResponse = await client.send_message(request=send_request)
                
                # The response from send_message is SendMessageResponse, which contains a Message
                host_agent_reply: Message = response.message
                
                # Extract text from the response message
                # Using get_message_text for robustness, though direct access is also possible.
                final_report_text = get_message_text(host_agent_reply)

                print("\n--- HostAgent Final Report ---")
                print(final_report_text)
                print("--- End of Report ---")

            except httpx.HTTPStatusError as e:
                print(f"HTTP error occurred while sending message: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"An error occurred while sending message or processing response: {e}")


    except httpx.ConnectError:
        print(f"Connection error: Could not connect to HostAgent at {HOST_AGENT_BASE_URL}.")
        print("Please ensure the multi-agent system (main.py) is running.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Starting HostAgent test client...")
    asyncio.run(main())
    print("\nTest client finished.")
