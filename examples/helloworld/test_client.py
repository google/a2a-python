import logging  # Import the logging module
from typing import Any
from uuid import uuid4

import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (AgentCard, MessageSendParams, SendMessageRequest,
                       SendStreamingMessageRequest)


async def main() -> None:
    PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"
    EXTENDED_AGENT_CARD_PATH = "/agent/authenticatedExtendedCard"

    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance

    base_url = 'http://localhost:9999'

    async with httpx.AsyncClient() as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )

        # Fetch Public Agent Card and Initialize Client
        public_agent_card: AgentCard | None = None
        extended_agent_card: AgentCard | None = None
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f"Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}")
            public_agent_card = await resolver.get_agent_card()  # Fetches from default public path
            logger.info("Successfully fetched public agent card:")
            logger.info(public_agent_card.model_dump_json(indent=2, exclude_none=True))

            # --- Conditional Step: Fetch Extended Agent Card
            if public_agent_card and public_agent_card.supportsAuthenticatedExtendedCard:
                logger.info(f"\nPublic card supports authenticated extended card. Attempting to fetch from: {base_url}{EXTENDED_AGENT_CARD_PATH}")
                auth_headers_dict = {"Authorization": "Bearer dummy-token-for-extended-card"}
                extended_agent_card = await resolver.get_agent_card(
                    relative_card_path=EXTENDED_AGENT_CARD_PATH, # Or resolver.extended_agent_card_path
                    http_kwargs={"headers": auth_headers_dict}
                )
                logger.info("Successfully fetched authenticated extended agent card:")
                logger.info(extended_agent_card.model_dump_json(indent=2, exclude_none=True))
            else:
                logger.info("\nPublic card does not support authenticated extended card, or public card not fetched.")

        except Exception as e:
            logger.error(f"Error during agent card fetching: {e}", exc_info=True)
            # If public card fetching failed, or extended card fetching failed after public card indicated support,
            # we might not have a card to use.

        # Determine which card to use and Initialize Client
        if extended_agent_card:
            final_agent_card_to_use = extended_agent_card
            logger.info("\nUsing AUTHENTICATED EXTENDED agent card for client initialization.")
        elif public_agent_card:
            final_agent_card_to_use = public_agent_card
            logger.info("\nUsing PUBLIC agent card for client initialization.")
        else:
            logger.error("\nNo agent card successfully fetched. Cannot initialize client.")
            return # Cannot proceed

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info("A2AClient initialized.")

        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'how much is 10 USD in INR?'}
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        streaming_request = SendStreamingMessageRequest(
            params=MessageSendParams(**send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)
        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
