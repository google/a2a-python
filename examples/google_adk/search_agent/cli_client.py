import argparse
import asyncio

from uuid import uuid4

import httpx

from a2a.client import A2AClient
from a2a.types import (
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
)


async def main():
    parser = argparse.ArgumentParser(
        description='CLI client for the Search Agent.'
    )
    parser.add_argument(
        '--query', type=str, required=True, help='The search query.'
    )
    parser.add_argument(
        '--location',
        type=str,
        default='USA',
        help='The location for the search (default: USA).',
    )
    args = parser.parse_args()

    agent_url = 'http://localhost:10009'

    async with httpx.AsyncClient() as httpx_client:
        client = A2AClient(url=agent_url, httpx_client=httpx_client)

        print(
            f"Sending query '{args.query}' for location '{args.location}' to agent at {agent_url}..."
        )

        try:
            send_message_payload = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {
                            'kind': 'text',
                            'text': f'Search for {args.query} in {args.location}',
                        }
                    ],
                    'messageId': uuid4().hex,
                },
                'agentId': 'search_agent',
                'userId': 'cli_user',
            }
            request = SendMessageRequest(
                params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)
            print('\nAgent Response:')
            if isinstance(response.root, SendMessageSuccessResponse):
                if isinstance(response.root.result, Task):
                    if response.root.result.artifacts:
                        for artifact in response.root.result.artifacts:
                            if artifact.parts:
                                for part in artifact.parts:
                                    if part.root.kind == 'text':
                                        print(part.root.text)
                                        break  # Assuming only one text part per artifact is relevant for display
                    # Removed else: print("No text content found in agent response artifacts.")
                # Removed else: print("No artifacts found in agent response.")
                elif isinstance(response.root.result, Message):
                    if response.root.result.parts:
                        for part in response.root.result.parts:
                            if part.root.kind == 'text':
                                print(part.root.text)
                                break  # Assuming only one text part per message is relevant for display
                        # Removed else: print("No text content found in agent response message.")
                    # Removed else: print("No parts found in agent response message.")
                # Removed else: print(f"Unexpected result type: {type(response.root.result)}")
            elif isinstance(response.root, JSONRPCErrorResponse):
                print(f'Agent returned an error: {response.root.error.message}')
            # Removed else: print("Could not parse agent response: Unknown response type.")
        except Exception as e:
            print(f'An error occurred: {e}')


if __name__ == '__main__':
    asyncio.run(main())
