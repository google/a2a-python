from typing import Any, Dict
import json
import os
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


async def upload_file(
    httpx_client: httpx.AsyncClient, api_key: str, file_path: str, user_id: str
) -> Dict[str, Any]:
    """Upload a file to the A2A server and return the file metadata."""
    upload_url = 'http://192.168.8.41:8080/v1/files/upload'

    # Prepare form data with the file
    files = {'file': open(file_path, 'rb')}
    form_data = {'user': user_id}

    headers = {'Authorization': f'Bearer {api_key}'}

    # Make the upload request
    response = await httpx_client.post(
        upload_url, files=files, data=form_data, headers=headers
    )

    if response.status_code not in [200, 201]:
        raise Exception(
            f'File upload failed with status code {response.status_code}: {response.text}'
        )

    return response.json()


async def main() -> None:
    # Set default values for parameters
    api_key = 'app-eoW3l7V3CyWX9H78FbBGTrje'  # API key
    user_id = 'kingstonwen104@gmail.com'  # User ID
    bank_statement_path = 'bank_statement.xlsx'  # Path to the bank statement file

    # Check if the file exists
    if not os.path.exists(bank_statement_path):
        # Try relative path from the script location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        bank_statement_path = os.path.join(script_dir, 'bank_statement.xlsx')
        if not os.path.exists(bank_statement_path):
            print(f'Error: File {bank_statement_path} not found!')
            return

    # List to store all response chunks
    all_responses = []

    # file_id = "edcbb8d0-6497-4e1c-b1a8-9a7a32274d14"

    async with httpx.AsyncClient() as httpx_client:
        # First, upload the bank statement file
        print(f'Uploading file {bank_statement_path}...')
        try:
            upload_response = await upload_file(
                httpx_client, api_key, bank_statement_path, user_id
            )
            print(
                f'File uploaded successfully. File ID: {upload_response["id"]}'
            )

            file_id = upload_response['id']
            file_type = 'document'
        except Exception as e:
            print(f'Error uploading file: {e}')
            return
        # else:
        #     print('skip upload file')
        #     file_type = 'document'

        # Get A2A client
        client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, 'http://localhost:8888'
        )

        # Build message payload with bank statement file ID
        data_payload: Dict[str, Any] = {
            'bank_statement': {
                'transfer_method': 'local_file',
                'upload_file_id': file_id,
                'type': file_type,
            },
            'api_key': api_key,
            'user_id': user_id
        }

        # Build message payload
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

        print('\nTesting streaming response with bank statement:')
        streaming_request = SendStreamingMessageRequest(
            params=MessageSendParams(**send_message_payload)
        )

        print(
            f'Sending message/stream request to A2A agent with bank statement file ID: {file_id}...'
        )

        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            # Convert response to JSON format
            response_json = chunk.model_dump(mode='json', exclude_none=True)
            all_responses.append(response_json)

            # Print the JSON response
            print(json.dumps(response_json, ensure_ascii=False, indent=2))

    # Save all responses to a JSON file
    with open('bank_report_output.json', 'w', encoding='utf-8') as f:
        json.dump(all_responses, f, ensure_ascii=False, indent=2)

    print(f'\nAll responses have been saved to bank_report_output.json')


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
