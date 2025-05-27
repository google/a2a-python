import argparse
import asyncio
import logging

from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2AClient
from a2a.types import (
    GetTaskRequest,
    GetTaskSuccessResponse,
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TaskQueryParams,
    TaskState,
    TextPart,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def poll_task_until_completion(
    client: A2AClient, task_id: str
) -> Task | None:
    """Polls the task status until it's completed or failed."""
    while True:
        logger.info(f'Polling task: {task_id}')
        query_params = TaskQueryParams(id=task_id)
        task_response = await client.get_task(
            GetTaskRequest(params=query_params)
        )

        if isinstance(task_response.root, JSONRPCErrorResponse):
            logger.error(
                f'Error getting task status: {task_response.root.error.message}'
            )
            return None

        if isinstance(
            task_response.root, GetTaskSuccessResponse
        ) and isinstance(task_response.root.result, Task):
            task = task_response.root.result
            logger.info(f'Task status: {task.status.state}')
            if task.status.message and task.status.message.parts:
                for part in task.status.message.parts:
                    if isinstance(part.root, TextPart):
                        logger.info(f'Agent interim message: {part.root.text}')

            if task.status.state in [
                TaskState.completed,
                TaskState.failed,
                TaskState.canceled,
            ]:
                logger.info(f'Task {task.status.state}.')
                return task
        else:
            logger.error(
                f'Unexpected response type when getting task: {task_response}'
            )
            return None

        await asyncio.sleep(2)  # Poll every 2 seconds.


async def main():
    parser = argparse.ArgumentParser(
        description='CLI client for the Translation Orchestrator Agent.'
    )
    parser.add_argument(
        '--query',
        type=str,
        required=True,
        help='The translation query (e.g., "Translate \'Hello world\' to Spanish").',
    )
    parser.add_argument(
        '--agent_url',
        type=str,
        default='http://localhost:10012',
        help='The URL of the Translation Orchestrator Agent.',
    )
    parser.add_argument(
        '--agent_id',
        type=str,
        default='translation_orchestrator',
        help='The agent ID to send the message to.',
    )
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as httpx_client:
        client = A2AClient(url=args.agent_url, httpx_client=httpx_client)

        logger.info(
            f"Sending query '{args.query}' to agent {args.agent_id} at {args.agent_url}..."
        )

        try:
            send_message_payload: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [{'kind': 'text', 'text': args.query}],
                    'messageId': uuid4().hex,
                },
                'agentId': args.agent_id,
                'userId': 'cli_user',
            }
            request = SendMessageRequest(
                params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)

            task_id_to_poll = None

            if isinstance(response.root, SendMessageSuccessResponse):
                if isinstance(response.root.result, Task):
                    task_id_to_poll = response.root.result.id
                    logger.info(
                        f'Message sent. Task ID: {task_id_to_poll}. Polling for completion...'
                    )
                elif isinstance(response.root.result, Message):
                    logger.warning(
                        'Received direct message response, expected task. This might indicate an issue.'
                    )
                    if response.root.result.parts:
                        for part_item in response.root.result.parts:
                            if isinstance(part_item.root, TextPart):
                                print(
                                    f'Agent direct response: {part_item.root.text}'
                                )
                else:
                    logger.error(
                        f'Unexpected result type in SendMessageSuccessResponse: {type(response.root.result)}'
                    )

            elif isinstance(response.root, JSONRPCErrorResponse):
                logger.error(
                    f'Agent returned an error on send_message: {response.root.error.message}'
                )
            else:
                logger.error(
                    f'Could not parse agent response: Unknown response type. {response}'
                )

            if task_id_to_poll:
                completed_task = await poll_task_until_completion(
                    client, task_id_to_poll
                )
                if completed_task and completed_task.artifacts:
                    print('\n--- Final Translation Result ---')
                    for artifact_item in completed_task.artifacts:
                        if artifact_item.parts:
                            for part_item in artifact_item.parts:
                                if isinstance(part_item.root, TextPart):
                                    print(part_item.root.text)
                elif (
                    completed_task
                    and completed_task.status.state == TaskState.failed
                ):
                    print('\n--- Task Failed ---')
                    if completed_task.status.error:
                        print(
                            f'Error: {completed_task.status.error.message} (Code: {completed_task.status.error.code})'
                        )
                else:
                    print(
                        '\nNo artifacts found in the completed task or task did not complete successfully.'
                    )

        except Exception as e:
            logger.error(f'An error occurred: {e}', exc_info=True)


if __name__ == '__main__':
    asyncio.run(main())
