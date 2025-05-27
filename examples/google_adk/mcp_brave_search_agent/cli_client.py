import asyncio
import argparse
import httpx
from uuid import uuid4
from a2a.client import A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendMessageSuccessResponse,
    JSONRPCErrorResponse,
    Task,
    Message,
)

async def main():
    parser = argparse.ArgumentParser(description="CLI client for the Brave Search Agent.")
    parser.add_argument("--query", type=str, required=True, help="The search query.")
    args = parser.parse_args()

    agent_url = "http://localhost:10009" # Ensure this matches the server port

    async with httpx.AsyncClient() as httpx_client:
        client = A2AClient(url=agent_url, httpx_client=httpx_client)

        print(f"Sending query '{args.query}' to agent at {agent_url}...")

        try:
            send_message_payload = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'kind': 'text', 'text': args.query}
                    ],
                    'messageId': uuid4().hex,
                },
                'agentId': "mcp_brave_search_agent_adk", # Matches LlmAgent name
                'userId': "cli_user",
            }
            request = SendMessageRequest(
                params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)
            print("\nAgent Response:")
            if isinstance(response.root, SendMessageSuccessResponse):
                if isinstance(response.root.result, Task):
                    if response.root.result.artifacts:
                        for artifact in response.root.result.artifacts:
                            if artifact.parts:
                                for part in artifact.parts:
                                    if part.root.kind == 'text':
                                        print(part.root.text)
                                        break
                elif isinstance(response.root.result, Message):
                    if response.root.result.parts:
                        for part in response.root.result.parts:
                            if part.root.kind == 'text':
                                print(part.root.text)
                                break
                else:
                    print(f"Unexpected result type: {type(response.root.result)}")
            elif isinstance(response.root, JSONRPCErrorResponse):
                print(f"Agent returned an error: {response.root.error.message}")
            else:
                print("Could not parse agent response: Unknown response type.")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
