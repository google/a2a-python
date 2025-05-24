import json
import uuid

from typing import Any, Dict

import httpx

from typing_extensions import override

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact


class DifyAgent:
    """Dify Agent wrapper for blocking mode requests only."""

    # Default API endpoints
    DEFAULT_API_URL = 'http://192.168.8.41:8080/v1/workflows/run'
    CLOUD_API_URL = 'https://api.dify.ai/v1/workflows/run'

    async def invoke(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP POST request to Dify API in blocking mode."""
        # Determine API URL based on server type
        url = (
            self.CLOUD_API_URL
            if data.get('dify_server') == 'cloud'
            else self.DEFAULT_API_URL
        )

        # Extract API key and user ID
        api_key = data.get('api_key')
        user_id = data.get('user_id')

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        # Create request parameters without special keys
        request_params = {
            k: v
            for k, v in data.items()
            if k not in ['api_key', 'user_id', 'dify_server']
        }

        # Prepare payload
        payload = {
            'inputs': request_params,
            'response_mode': 'blocking',
            'user': user_id,
        }

        print(f'Sending payload to Dify: {json.dumps(payload, indent=2)}')

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f'Error calling Dify API: {str(e)}')


class DifyBlockingAgentExecutor(AgentExecutor):
    """Dify Agent Executor Implementation for blocking mode only."""

    def __init__(self):
        self.agent = DifyAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # Extract data payload from message parts
        data = self._extract_data_from_message(context.message)

        # Initialize task
        task = self._initialize_task(context, event_queue, data)

        try:
            # Send initial status update
            self._send_working_status(
                task, event_queue, 'Processing request...'
            )

            # Call Dify API in blocking mode
            response = await self.agent.invoke(data)

            # Extract the result text
            result_text = self._extract_result_text(response)

            # Create artifact with the result
            self._create_result_artifact(task, event_queue, result_text, data)

            # Mark task as completed
            self._send_completed_status(task, event_queue, result_text)

        except Exception as e:
            # Handle errors
            error_message = f'Error: {str(e)}'
            self._send_failed_status(task, event_queue, error_message)

    def _extract_data_from_message(self, message) -> Dict[str, Any]:
        """Extract data payload from message parts."""
        data = {}
        for part in message.parts:
            if hasattr(part.root, 'data'):
                data = part.root.data
        return data

    def _initialize_task(self, context, event_queue, data) -> Any:
        """Initialize task."""
        task = context.current_task
        if not task:
            print('Creating new task')
            task = new_task(context.message)
            event_queue.enqueue_event(task)
        return task

    def _send_working_status(self, task, event_queue, message_text):
        """Send working status update."""
        message = new_agent_text_message(message_text, task.contextId, task.id)
        event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(
                    state=TaskState.working,
                    message=message,
                ),
                final=False,
                contextId=task.contextId,
                taskId=task.id,
            )
        )

    def _send_completed_status(self, task, event_queue, message_text):
        """Send completed status update."""
        message = new_agent_text_message(message_text, task.contextId, task.id)
        event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(
                    state=TaskState.completed,
                    message=message,
                ),
                final=True,
                contextId=task.contextId,
                taskId=task.id,
            )
        )

    def _send_failed_status(self, task, event_queue, error_message):
        """Send failed status update."""
        message = new_agent_text_message(error_message, task.contextId, task.id)
        event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(
                    state=TaskState.failed,
                    message=message,
                ),
                final=True,
                contextId=task.contextId,
                taskId=task.id,
            )
        )

    def _extract_result_text(self, response) -> str:
        """Extract result text from Dify API response."""
        # First try to get text directly
        if 'text' in response:
            return response['text']

        # Then try to get from outputs
        if 'outputs' in response and 'text' in response['outputs']:
            return response['outputs']['text']

        # If no text found, return the whole response as JSON
        return json.dumps(response, indent=2, ensure_ascii=False)

    def _create_result_artifact(self, task, event_queue, result_text, data):
        """Create artifact with the result."""
        # Create artifact description based on task
        artifact_description = self._get_artifact_description(data)

        event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                append=False,
                contextId=task.contextId,
                taskId=task.id,
                lastChunk=True,
                artifact=new_text_artifact(
                    name='result',
                    description=artifact_description,
                    text=result_text,
                ),
            )
        )

    def _get_artifact_description(self, data: Dict[str, Any]) -> str:
        """Generate artifact description based on the data."""
        if 'city' in data:
            return f'Weather information for {data["city"]}'
        elif 'bank_statement' in data:
            return 'Bank statement analysis results'
        return 'Dify workflow result'

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
