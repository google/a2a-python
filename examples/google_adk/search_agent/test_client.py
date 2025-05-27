import logging
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (AgentCard, MessageSendParams, SendMessageRequest,
                       SendStreamingMessageRequest)


async def main() -> None:
    PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    base_url = 'http://localhost:10009' # Port for the search agent

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )

        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f"Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}")
            _public_card = await resolver.get_agent_card()
            logger.info("Successfully fetched public agent card:")
            logger.info(_public_card.model_dump_json(indent=2, exclude_none=True))
            final_agent_card_to_use = _public_card
            logger.info("\nUsing PUBLIC agent card for client initialization.")

        except Exception as e:
            logger.error(f"Critical error fetching public agent card: {e}", exc_info=True)
            raise RuntimeError("Failed to fetch the public agent card. Cannot continue.") from e

       
        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info("A2AClient initialized.")

        # Test cases
        test_queries = [
            "Find coffee shops near 90210",
            "What's the weather in London 12345?",
            "Latest news about AI in San Francisco",
            "Best parks in New York City 10001",
        ]

        for query in test_queries:
            print(f"\n--- Sending query: '{query}' ---")
            send_message_payload: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'kind': 'text', 'text': query}
                    ],
                    'messageId': uuid4().hex,
                },
            }
            request = SendMessageRequest(
                params=MessageSendParams(**send_message_payload)
            )

            response = await client.send_message(request)
            print("Non-streaming response:")
            print(response.model_dump(mode='json', exclude_none=True))

            print(f"\n--- Sending streaming query: '{query}' ---")
            streaming_request = SendStreamingMessageRequest(
                params=MessageSendParams(**send_message_payload)
            )

            stream_response = client.send_message_streaming(streaming_request)
            async for chunk in stream_response:
                print("Streaming chunk:")
                print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
