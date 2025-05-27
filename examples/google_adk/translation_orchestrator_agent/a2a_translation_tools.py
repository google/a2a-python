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

# Configuration for sub-agent endpoints
SPANISH_AGENT_URL = 'http://localhost:10010'
SPANISH_AGENT_ID = 'spanish_translator'
FRENCH_AGENT_URL = 'http://localhost:10011'
FRENCH_AGENT_ID = 'french_translator'

# Configuration for Brave Search MCP Agent
BRAVE_SEARCH_AGENT_URL = 'http://localhost:10009'
BRAVE_SEARCH_AGENT_ID = 'mcp_brave_search_agent_adk'


async def _call_a2a_agent(
    agent_url: str, agent_id: str, message_text: str
) -> str:
    """Helper function to call an external A2A agent and poll for results.
    This function sends a message to the specified agent and waits for task completion.
    """
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        a2a_client = A2AClient(url=agent_url, httpx_client=http_client)

        message_to_agent = Message(
            role='user',
            parts=[TextPart(text=message_text)],
            messageId=uuid4().hex,
        )

        send_params = MessageSendParams(
            message=message_to_agent,
            agentId=agent_id,
            userId='orchestrator_user_id',
        )
        request = SendMessageRequest(params=send_params)

        try:
            response = await a2a_client.send_message(request)
            task_id_to_poll = None

            if isinstance(
                response.root, SendMessageSuccessResponse
            ) and isinstance(response.root.result, Task):
                task_id_to_poll = response.root.result.id
            elif isinstance(response.root, JSONRPCErrorResponse):
                logger.error(
                    f'Error sending message to {agent_id} at {agent_url}: {response.root.error.message}'
                )
                return (
                    f'Error calling {agent_id}: {response.root.error.message}'
                )
            else:
                logger.error(
                    f'Unexpected response from {agent_id} at {agent_url}: {response}'
                )
                return f'Unexpected response from {agent_id}.'

            if task_id_to_poll:
                while True:
                    await asyncio.sleep(1)
                    query_params = TaskQueryParams(id=task_id_to_poll)
                    task_response = await a2a_client.get_task(
                        GetTaskRequest(params=query_params)
                    )
                    if isinstance(
                        task_response.root, GetTaskSuccessResponse
                    ) and isinstance(task_response.root.result, Task):
                        task = task_response.root.result
                        if task.status.state == TaskState.completed:
                            if task.artifacts:
                                for artifact in task.artifacts:
                                    if artifact.parts:
                                        for part in artifact.parts:
                                            if isinstance(part.root, TextPart):
                                                return part.root.text
                            return 'Task completed but no text artifact found.'
                        if task.status.state in [
                            TaskState.failed,
                            TaskState.canceled,
                            TaskState.rejected,
                        ]:
                            error_msg = (
                                task.status.error.message
                                if task.status.error
                                else 'Task failed without specific error.'
                            )
                            logger.error(
                                f'Task {task_id_to_poll} for {agent_id} failed: {error_msg}'
                            )
                            return f'{agent_id} task failed: {error_msg}'
                    elif isinstance(task_response.root, JSONRPCErrorResponse):
                        logger.error(
                            f'Error polling task {task_id_to_poll} for {agent_id}: {task_response.root.error.message}'
                        )
                        return f'Error polling {agent_id} task: {task_response.root.error.message}'
                    else:
                        logger.error(
                            f'Unexpected polling response for {agent_id} task {task_id_to_poll}: {task_response}'
                        )
                        return f'Unexpected polling response from {agent_id}.'
        except Exception as e:
            logger.error(
                f'Exception calling A2A agent {agent_id} at {agent_url}: {e}',
                exc_info=True,
            )
            return f'Exception calling {agent_id}: {e!s}'
    return f'Failed to get response from {agent_id}.'


async def translate_to_spanish_function(
    text_to_translate: str, original_user_query: str
) -> dict[str, Any]:
    """Translates a given text to Spanish by calling an external Spanish translation agent.
    Use this tool when the target language is Spanish.

    Args:
        text_to_translate (str): The specific text that needs to be translated into Spanish.
        original_user_query (str): The full original query from the user, for context.

    Returns:
        dict: A dictionary containing the 'translated_text' or an error message.
    """
    logger.info(
        f"translate_to_spanish_function: Called for text '{text_to_translate}' from query '{original_user_query}'"
    )
    translation = await _call_a2a_agent(
        SPANISH_AGENT_URL, SPANISH_AGENT_ID, text_to_translate
    )
    return {'translated_text': translation}


async def translate_to_french_function(
    text_to_translate: str, original_user_query: str
) -> dict[str, Any]:
    """Translates a given text to French by calling an external French translation agent.
    Use this tool when the target language is French.

    Args:
        text_to_translate (str): The specific text that needs to be translated into French.
        original_user_query (str): The full original query from the user, for context.

    Returns:
        dict: A dictionary containing the 'translated_text' or an error message.
    """
    logger.info(
        f"translate_to_french_function: Called for text '{text_to_translate}' from query '{original_user_query}'"
    )
    translation = await _call_a2a_agent(
        FRENCH_AGENT_URL, FRENCH_AGENT_ID, text_to_translate
    )
    return {'translated_text': translation}


async def search_and_translate_news_function(
    search_query: str, target_language: str, original_user_query: str
) -> dict[str, Any]:
    """Searches for news using the Brave Search MCP agent and then translates the results
    to the specified target language (Spanish or French).

    Args:
        search_query (str): The query to use for searching news (e.g., "latest AI news").
        target_language (str): The language to translate the news into (e.g., "Spanish", "French").
        original_user_query (str): The full original query from the user, for context.

    Returns:
        dict: A dictionary containing the 'translated_news' or an error message.
    """
    logger.info(
        f"search_and_translate_news_function: Called for query '{search_query}' to translate to '{target_language}' from original query '{original_user_query}'"
    )

    # Step 1: Call the Brave Search MCP agent
    search_results = await _call_a2a_agent(
        BRAVE_SEARCH_AGENT_URL, BRAVE_SEARCH_AGENT_ID, search_query
    )
    logger.info(f'Brave Search results: {search_results}')

    if (
        search_results.startswith('Error')
        or search_results.startswith('Unexpected')
        or search_results.startswith('Failed')
    ):
        return {'translated_news': f'Failed to get news: {search_results}'}

    # Step 2: Extract relevant text from search results for translation
    # For simplicity, let's assume the search_results string contains the main text to translate.
    # In a real scenario, you might parse JSON results to get snippets/titles.
    text_to_translate = f"News results for '{search_query}': {search_results}"

    # Step 3: Delegate to the appropriate translation function
    if target_language.lower() == 'spanish':
        translation_result = await translate_to_spanish_function(
            text_to_translate, original_user_query
        )
    elif target_language.lower() == 'french':
        translation_result = await translate_to_french_function(
            text_to_translate, original_user_query
        )
    else:
        return {
            'translated_news': f'Unsupported translation language: {target_language}. Only Spanish and French are supported.'
        }

    return {
        'translated_news': translation_result.get(
            'translated_text', 'Translation failed.'
        )
    }
