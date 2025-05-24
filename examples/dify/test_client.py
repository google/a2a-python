from typing import Any, Dict
import json
from uuid import uuid4

import httpx
from a2a.client import A2AClient
from a2a.types import (
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageResponse,
    SendStreamingMessageRequest,
    MessageSendConfiguration,
)


async def main() -> None:
    # Set default values for parameters
    # Define a generic data payload with multiple fields
    data_payload: Dict[str, Any] = {
        'city': '深圳',  # Default city
        'api_key': 'app-SXqTiCm89mGr2IJhKvwWgR7s',  # API key
        'user_id': 'kingstonwen104@gmail.com',  # User ID
        'dify_server': 'cloud'
    }
    response_mode = 'blocking'  # Default response mode

    # List to store all response chunks
    all_responses = []

    async with httpx.AsyncClient() as httpx_client:
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, 'http://localhost:8888'
        )

        # Build message payload with complete data payload as DataPart
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'type': 'data', 'data': data_payload},
                ],
                'messageId': uuid4().hex,
            },
            'configuration': {
                'blocking': True,
                'acceptedOutputModes': ['text/plain', 'application/json'],
            },
        }
        request = SendMessageRequest(
            params=MessageSendParams(**send_message_payload)
        )

        # print(f'Sending request to Dify agent with data: {json.dumps(data_payload, ensure_ascii=False)}...')
        # response = await client.send_message(request)
        # print(response.model_dump(mode='json', exclude_none=True))

        print('\nTesting streaming response:')
        # For streaming, use streaming mode configuration

        streaming_request = SendStreamingMessageRequest(
            params=MessageSendParams(**send_message_payload)
        )

        print(
            f'Sending message/stream request to Dify agent with data: {json.dumps(data_payload, ensure_ascii=False)}...'
        )

        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            # Convert response to JSON format
            response_json = chunk.model_dump(mode='json', exclude_none=True)
            all_responses.append(response_json)

            # Print the JSON response
            print(json.dumps(response_json, ensure_ascii=False, indent=2))

    # Save all responses to a JSON file
    with open('dify_output.json', 'w', encoding='utf-8') as f:
        json.dump(all_responses, f, ensure_ascii=False, indent=2)

    print(f'\nAll responses have been saved to dify_output.json')


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
