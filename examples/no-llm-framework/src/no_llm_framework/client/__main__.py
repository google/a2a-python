import asyncio
from typing import Literal
from uuid import uuid4

import asyncclick as click
import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    SendStreamingMessageSuccessResponse,
    TaskStatusUpdateEvent,
    TextPart,
)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=9999)
@click.option('--mode', 'mode', default='streaming')
async def a_main(
    host: str, port: int, mode: Literal['completion', 'streaming']
):
    """Main function to run the A2A Repo Agent client.

    Args:
        host (str): The host address to run the server on.
        port (int): The port number to run the server on.
        mode (Literal['completion', 'streaming']): The mode to run the server on.
    """  # noqa: E501
    async with httpx.AsyncClient() as httpx_client:
        card_resolver = A2ACardResolver(httpx_client, f'http://{host}:{port}')
        agent_card = await card_resolver.get_agent_card()
        agent_card.url = f'http://{host}:{port}'

        client = A2AClient(httpx_client, agent_card=agent_card)

        message = MessageSendParams(
            message=Message(
                role=Role.user,
                parts=[Part(TextPart(text='What is Google A2A?'))],
                messageId=uuid4().hex,
                taskId=uuid4().hex,
            )
        )

        if mode == 'completion':
            raise NotImplementedError('Completion mode not implemented')

        streaming_request = SendStreamingMessageRequest(params=message)
        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            if isinstance(
                chunk.root, SendStreamingMessageSuccessResponse
            ) and isinstance(chunk.root.result, TaskStatusUpdateEvent):
                message = chunk.root.result.status.message
                if message:
                    print(message.parts[0].root.text, end='', flush=True)


def main() -> None:
    """Main function to run the A2A Repo Agent client."""
    asyncio.run(a_main())


if __name__ == '__main__':
    main()
