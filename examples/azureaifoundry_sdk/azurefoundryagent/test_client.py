import logging  # Import the logging module
import os
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (AgentCard, MessageSendParams, SendMessageRequest,
                       SendStreamingMessageRequest)


async def test_agent_health(base_url: str, httpx_client: httpx.AsyncClient, logger: logging.Logger) -> bool:
    """Test if the agent server is healthy and responsive."""
    try:
        health_url = f"{base_url}/health"
        logger.info(f"🏥 Checking agent health at: {health_url}")
        
        response = await httpx_client.get(health_url)
        if response.status_code == 200:
            logger.info("✅ Agent server is healthy and responsive")
            return True
        else:
            logger.warning(f"⚠️  Agent health check returned status: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Agent health check failed: {e}")
        return False


async def print_detailed_response(response: Any, logger: logging.Logger, response_type: str = "Response"):
    """Print detailed response information in a readable format."""
    try:
        response_dict = response.model_dump(mode='json', exclude_none=True)
        logger.info(f"📋 {response_type} Details:")
        
        if 'message' in response_dict:
            message = response_dict['message']
            if 'parts' in message:
                for i, part in enumerate(message['parts']):
                    if part.get('kind') == 'text':
                        logger.info(f"   Part {i+1} (text): {part.get('text', '')[:100]}...")
        
        if 'status' in response_dict:
            logger.info(f"   Status: {response_dict['status']}")
            
    except Exception as e:
        logger.debug(f"Could not parse response details: {e}")


async def main() -> None:
    """
    Test client for AI Foundry Calendar Agent A2A demo.
    Tests both public and extended agent card functionality.
    """
    # Load environment variables
    load_dotenv()
    
    PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"
    EXTENDED_AGENT_CARD_PATH = "/agent/authenticatedExtendedCard"

    # Configure logging to show INFO level messages
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(level_name)s - %(message)s')
    logger = logging.getLogger(__name__)  # Get a logger instance

    # Use environment variable or default to our AI Foundry agent port
    base_url = os.getenv('A2A_BASE_URL', 'http://localhost:10007')
    logger.info(f"🔗 Connecting to AI Foundry Calendar Agent at: {base_url}")

    async with httpx.AsyncClient(timeout=30.0) as httpx_client:
        # First, test agent health
        if not await test_agent_health(base_url, httpx_client, logger):
            logger.error("❌ Agent server appears to be unhealthy. Please check the server.")
            return
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
            # agent_card_path uses default, extended_agent_card_path also uses default
        )

        # Fetch Public Agent Card and Initialize Client
        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f"🔍 Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}")
            _public_card = await resolver.get_agent_card()  # Fetches from default public path
            logger.info("✅ Successfully fetched public agent card:")
            logger.info(f"   Agent Name: {_public_card.name}")
            logger.info(f"   Description: {_public_card.description}")
            logger.info(f"   Skills: {len(_public_card.skills)} available")
            for skill in _public_card.skills:
                logger.info(f"     - {skill.name}: {skill.description}")
            
            final_agent_card_to_use = _public_card
            logger.info("\n📋 Using PUBLIC agent card for client initialization (default).")

            if _public_card.supportsAuthenticatedExtendedCard:
                try:
                    logger.info(f"\n🔒 Public card supports authenticated extended card. Attempting to fetch from: {base_url}{EXTENDED_AGENT_CARD_PATH}")
                    auth_headers_dict = {"Authorization": "Bearer demo-token-for-foundry-agent"}
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={"headers": auth_headers_dict}
                    )
                    logger.info("✅ Successfully fetched authenticated extended agent card:")
                    logger.info(f"   Extended Agent Name: {_extended_card.name}")
                    logger.info(f"   Additional Capabilities: {_extended_card.capabilities}")
                    final_agent_card_to_use = _extended_card # Update to use the extended card
                    logger.info("\n🔐 Using AUTHENTICATED EXTENDED agent card for client initialization.")
                except Exception as e_extended:
                    logger.warning(f"⚠️  Failed to fetch extended agent card: {e_extended}. Will proceed with public card.")
            elif _public_card: # supportsAuthenticatedExtendedCard is False or None
                logger.info("\n📖 Public card does not indicate support for an extended card. Using public card.")

        except Exception as e:
            logger.error(f"❌ Critical error fetching public agent card: {e}")
            logger.info("💡 Make sure the AI Foundry Calendar Agent server is running:")
            logger.info(f"   uv run .")
            raise RuntimeError("Failed to fetch the public agent card. Cannot continue.") from e

        # Initialize A2A Client
        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        logger.info("✅ A2AClient initialized.")

        # Test calendar-specific queries
        calendar_test_messages = [
            "Hello! Can you help me with my calendar?",
            "Am I free tomorrow from 2 PM to 3 PM?", 
            "What meetings do I have coming up today?",
            "Help me find the best time for a 1-hour meeting this week.",
            "Can you check my availability for next Tuesday afternoon?"
        ]

        logger.info(f"\n🧪 Testing {len(calendar_test_messages)} calendar-related queries:")
        
        for i, test_message in enumerate(calendar_test_messages, 1):
            logger.info(f"\n--- Test {i}/{ len(calendar_test_messages)} ---")
            logger.info(f"💬 User: {test_message}")
            
            send_message_payload: dict[str, Any] = {
                'message': {
                    'role': 'user',
                    'parts': [
                        {'kind': 'text', 'text': test_message}
                    ],
                    'messageId': uuid4().hex,
                },
            }
            
            try:
                # Test regular message sending
                request = SendMessageRequest(
                    params=MessageSendParams(**send_message_payload)
                )
                
                logger.info("📤 Sending message...")
                response = await client.send_message(request)
                await print_detailed_response(response, logger, "Regular Message Response")
                
                # Test streaming message sending
                logger.info("🌊 Testing streaming response...")
                streaming_request = SendStreamingMessageRequest(
                    params=MessageSendParams(**send_message_payload)
                )
                
                stream_response = client.send_message_streaming(streaming_request)
                chunk_count = 0
                async for chunk in stream_response:
                    chunk_count += 1
                    if chunk_count == 1:
                        logger.info(f"📺 Streaming started (chunk {chunk_count})")
                    elif chunk_count <= 3:  # Show first few chunks
                        logger.info(f"📺 Chunk {chunk_count} received")
                
                logger.info(f"✅ Streaming completed ({chunk_count} chunks total)")
                
            except Exception as e:
                logger.error(f"❌ Error testing message '{test_message[:30]}...': {e}")
        
        logger.info("\n🎉 Calendar agent testing completed!")
        logger.info("📊 Test Summary:")
        logger.info(f"   - Agent: {final_agent_card_to_use.name}")
        logger.info(f"   - Base URL: {base_url}")
        logger.info(f"   - Test Messages: {len(calendar_test_messages)}")
        logger.info("   - Both regular and streaming messaging tested")


if __name__ == '__main__':
    import asyncio
    
    print("🤖 AI Foundry Calendar Agent - A2A Test Client")
    print("=" * 50)
    print("This client tests the Agent-to-Agent communication")
    print("with our AI Foundry Calendar Agent.")
    print("Make sure the agent server is running first!")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test client stopped by user")
    except Exception as e:
        print(f"\n❌ Test client failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Ensure the AI Foundry agent server is running")
        print("2. Check your .env configuration")
        print("3. Verify network connectivity")
        print("4. Check logs for detailed error information")
