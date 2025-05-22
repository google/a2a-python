import asyncio
import json
import time
import uuid

from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set

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


class DifyEvent(StrEnum):
    """Dify event types enum."""

    # Text generation events
    LLM_CHUNK = 'llm_chunk'
    TEXT_CHUNK = 'text_chunk'

    # Message events
    AGENT_MESSAGE = 'agent_message'
    MESSAGE_REPLACE = 'message_replace'
    MESSAGE_END = 'message_end'
    ADVANCED_CHAT_MESSAGE_END = 'advanced_chat_message_end'
    MESSAGE_FILE = 'message_file'

    # Workflow events
    WORKFLOW_STARTED = 'workflow_started'
    WORKFLOW_SUCCEEDED = 'workflow_succeeded'
    WORKFLOW_FAILED = 'workflow_failed'
    WORKFLOW_FINISHED = 'workflow_finished'
    WORKFLOW_PARTIAL_SUCCEEDED = 'workflow_partial_succeeded'

    # Iteration events
    ITERATION_START = 'iteration_start'
    ITERATION_NEXT = 'iteration_next'
    ITERATION_COMPLETED = 'iteration_completed'

    # Loop events
    LOOP_START = 'loop_start'
    LOOP_NEXT = 'loop_next'
    LOOP_COMPLETED = 'loop_completed'

    # Node events
    NODE_STARTED = 'node_started'
    NODE_SUCCEEDED = 'node_succeeded'
    NODE_FAILED = 'node_failed'
    NODE_FINISHED = 'node_finished'
    NODE_EXCEPTION = 'node_exception'

    # Agent events
    AGENT_THOUGHT = 'agent_thought'
    AGENT_LOG = 'agent_log'

    # Retrieval events
    RETRIEVER_RESOURCES = 'retriever_resources'
    ANNOTATION_REPLY = 'annotation_reply'

    # Parallel processing events
    PARALLEL_BRANCH_RUN_STARTED = 'parallel_branch_run_started'
    PARALLEL_BRANCH_RUN_SUCCEEDED = 'parallel_branch_run_succeeded'
    PARALLEL_BRANCH_RUN_FAILED = 'parallel_branch_run_failed'

    # System events
    ERROR = 'error'
    PING = 'ping'
    STOP = 'stop'
    RETRY = 'retry'


class DifyAgent:
    """Dify Agent wrapper for interacting with Dify API."""

    # Default API endpoints
    DEFAULT_API_URL = 'http://192.168.8.41:8080/v1/workflows/run'
    CLOUD_API_URL = 'https://api.dify.ai/v1/workflows/run'

    # Events configuration
    SKIP_EVENTS = {
        DifyEvent.PING,
        DifyEvent.ITERATION_NEXT,
        DifyEvent.LOOP_NEXT,
        DifyEvent.TEXT_CHUNK,
    }

    IMPORTANT_EVENTS = {
        DifyEvent.WORKFLOW_STARTED,
        DifyEvent.WORKFLOW_SUCCEEDED,
        DifyEvent.WORKFLOW_FAILED,
        DifyEvent.WORKFLOW_FINISHED,
        DifyEvent.WORKFLOW_PARTIAL_SUCCEEDED,
        DifyEvent.NODE_STARTED,
        DifyEvent.NODE_SUCCEEDED,
        DifyEvent.NODE_FAILED,
        DifyEvent.NODE_FINISHED,
        DifyEvent.NODE_EXCEPTION,
    }

    def _prepare_request(
        self, data: Dict[str, Any], response_mode: str
    ) -> tuple[str, Dict[str, str], Dict[str, Any]]:
        """Prepare the request URL, headers and payload for Dify API."""
        # Determine API URL based on server type
        url = (
            self.CLOUD_API_URL
            if data.get('dify_server') == 'cloud'
            else self.DEFAULT_API_URL
        )

        # Extract API key and user ID
        api_key = data.get('api_key')
        user_id = data.get('user_id')

        # Prepare headers
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        # For streaming requests, add Accept header
        if response_mode == 'streaming':
            headers['Accept'] = 'text/event-stream'

        # Create request parameters without special keys
        request_params = {
            k: v
            for k, v in data.items()
            if k not in ['api_key', 'user_id', 'dify_server']
        }

        # Prepare payload
        payload = {
            'inputs': request_params,
            'response_mode': response_mode,
            'user': user_id,
        }

        return url, headers, payload

    async def invoke(
        self, data: Dict[str, Any], response_mode: str = 'blocking'
    ) -> str:
        """Make HTTP POST request to Dify API in blocking mode."""
        url, headers, payload = self._prepare_request(data, response_mode)

        print(f'Sending payload to Dify: {json.dumps(payload, indent=2)}')

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return f'Dify API Response: {response.json()}'
            except httpx.HTTPError as e:
                return f'Error calling Dify API: {str(e)}'

    async def stream(
        self, data: Dict[str, Any], task_id: str
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream responses from Dify API, filtering out unimportant events."""
        url, headers, payload = self._prepare_request(data, 'streaming')

        print(
            f'Sending streaming payload to Dify: {json.dumps(payload, indent=2)}'
        )

        # Prepare file for raw SSE results
        timestamp = int(time.time())
        raw_sse_file = f'dify_raw_sse_response.json'
        raw_sse_events = []

        async with (
            httpx.AsyncClient(timeout=20.0) as client,
            client.stream(
                'POST', url, json=payload, headers=headers
            ) as response,
        ):
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line.startswith('data: '):
                    continue

                try:
                    raw_data = line[6:]  # Remove 'data: ' prefix
                    data = json.loads(raw_data)

                    # Store raw SSE event
                    raw_sse_events.append(data)

                    event_type = data.get('event')
                    node_data = data.get('data', {})
                    node_type = node_data.get('node_type', '')

                    # Skip low-level events
                    if event_type in self.SKIP_EVENTS:
                        continue

                    # Handle text chunks for real-time updates
                    if (
                        event_type == DifyEvent.TEXT_CHUNK
                        and 'text' in node_data
                    ):
                        continue

                    # Handle workflow_finished event
                    if event_type == DifyEvent.WORKFLOW_FINISHED:
                        yield self._handle_workflow_finished(data)
                        break

                    # Process node events with detailed information
                    if event_type in [
                        DifyEvent.NODE_STARTED,
                        DifyEvent.NODE_FINISHED,
                    ]:
                        yield self._handle_node_event(
                            data, event_type, node_data, node_type
                        )
                        continue

                    # Pass through other important events
                    if event_type in self.IMPORTANT_EVENTS:
                        yield self._handle_important_event(data, event_type)

                except json.JSONDecodeError:
                    continue

            # Save all raw SSE events to file
            with open(raw_sse_file, 'w', encoding='utf-8') as f:
                json.dump(raw_sse_events, f, ensure_ascii=False, indent=2)
            print(f'Raw SSE events saved to {raw_sse_file}')

    def _handle_workflow_finished(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle workflow_finished event and extract final text."""
        # Get the final text output
        final_text = data.get('data', {}).get('text', '')
        if not final_text and 'outputs' in data.get('data', {}):
            final_text = data.get('data', {}).get('outputs', {}).get('text', '')

        return {
            'event': DifyEvent.WORKFLOW_FINISHED,
            'content': final_text,
            'is_task_complete': True,
            'require_user_input': False,
            'data': data.get('data', {}),
            'workflow_run_id': data.get('workflow_run_id'),
            'task_id': data.get('task_id'),
        }

    def _handle_node_event(
        self,
        data: Dict[str, Any],
        event_type: str,
        node_data: Dict[str, Any],
        node_type: str,
    ) -> Dict[str, Any]:
        """Handle node events (started/finished) with detailed information."""
        title = node_data.get('title', '')
        status = node_data.get('status', '')
        node_id = node_data.get('id', '')

        # Get outputs for node_finished events
        outputs = {}
        if event_type == DifyEvent.NODE_FINISHED:
            outputs = node_data.get('outputs', {})

        # Extract meaningful info from the event
        event_info = f' - {title}' if title else ''
        if node_type:
            event_info += f' ({node_type})'
        if status and event_type == DifyEvent.NODE_FINISHED:
            event_info += f' - {status}'

        return {
            'event': event_type,
            'content': f'{event_type.replace("_", " ").title()}{event_info}',
            'is_task_complete': False,
            'require_user_input': False,
            'data': node_data,
            'node_type': node_type,
            'title': title,
            'outputs': outputs,
            'status': status,
            'node_id': node_id,
            'workflow_run_id': data.get('workflow_run_id'),
            'task_id': data.get('task_id'),
        }

    def _handle_important_event(
        self, data: Dict[str, Any], event_type: str
    ) -> Dict[str, Any]:
        """Handle other important events."""
        # Extract meaningful info from the event
        event_info = ''
        if 'data' in data and 'title' in data['data']:
            event_info = f' - {data["data"]["title"]}'

        return {
            'event': event_type,
            'content': f'{event_type.replace("_", " ").title()}{event_info}',
            'is_task_complete': False,
            'require_user_input': False,
            'data': data.get('data', {}),
            'workflow_run_id': data.get('workflow_run_id'),
            'task_id': data.get('task_id'),
        }


class DifyAgentExecutor(AgentExecutor):
    """Dify Agent Executor Implementation for A2A integration."""

    def __init__(self):
        self.agent = DifyAgent()
        self.step_artifacts = {}  # Map to store artifacts by node_id

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

        # Process streaming response from agent
        await self._process_agent_stream(task, data, event_queue)

    def _extract_data_from_message(self, message) -> Dict[str, Any]:
        """Extract data payload from message parts."""
        data = {}
        for part in message.parts:
            if hasattr(part.root, 'data'):
                data = part.root.data
        return data

    def _initialize_task(self, context, event_queue, data) -> Any:
        """Initialize task and send initial status update."""
        task = context.current_task
        if not task:
            print('Creating new task')
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        # Create a task description based on available data
        task_description = self._get_task_description(data)

        # Send initial working status
        initial_message = new_agent_text_message(
            f'{task_description}...', task.contextId, task.id
        )
        event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(
                    state=TaskState.working,
                    message=initial_message,
                ),
                final=False,
                contextId=task.contextId,
                taskId=task.id,
            )
        )

        return task

    def _get_task_description(self, data: Dict[str, Any]) -> str:
        """Generate a task description based on the data."""
        if 'city' in data:
            return f'Processing weather request for {data["city"]}'
        elif 'bank_statement' in data:
            return 'Processing bank statement analysis'
        return 'Processing Dify workflow'

    async def _process_agent_stream(self, task, data, event_queue) -> None:
        """Process streaming response from agent."""
        async for event in self.agent.stream(data, task.id):
            if event['is_task_complete']:
                await self._handle_completed_task(
                    task, event, data, event_queue
                )
            else:
                await self._handle_working_task(task, event, event_queue)

    async def _handle_completed_task(
        self, task, event, data, event_queue
    ) -> None:
        """Handle completed task with final artifact and status update."""
        final_text = event['content']

        # Create artifact description based on task
        artifact_description = self._get_artifact_description(data)

        # Create final artifact
        event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                append=False,
                contextId=task.contextId,
                taskId=task.id,
                lastChunk=True,
                artifact=new_text_artifact(
                    name='result',
                    description=artifact_description,
                    text=final_text,
                ),
            )
        )

        # Final message with the result
        final_message = new_agent_text_message(
            final_text, task.contextId, task.id
        )

        # Mark task as completed
        event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                status=TaskStatus(
                    state=TaskState.completed,
                    message=final_message,
                ),
                final=True,
                contextId=task.contextId,
                taskId=task.id,
            )
        )

    def _get_artifact_description(self, data: Dict[str, Any]) -> str:
        """Generate artifact description based on the data."""
        if 'city' in data:
            return f'Weather information for {data["city"]}'
        elif 'bank_statement' in data:
            return 'Bank statement analysis results'
        return 'Dify workflow result'

    async def _handle_working_task(self, task, event, event_queue) -> None:
        """Handle task in working state with status updates."""
        event_name = event.get('event', '')
        content = event['content']

        # Create a message with additional metadata
        message = new_agent_text_message(content, task.contextId, task.id)

        # Add metadata to the message
        message.metadata = self._create_event_metadata(event, event_name)

        # Create artifacts for specific node types if needed
        if event_name == DifyEvent.NODE_FINISHED:
            await self._create_node_artifacts(task, event, event_queue)

        # Send update to client
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

    def _create_event_metadata(
        self, event: Dict[str, Any], event_name: str
    ) -> Dict[str, Any]:
        """Create metadata for the event message."""
        metadata = {
            'dify_event': event_name,
        }

        # Add node-specific information if available
        for field in ['node_type', 'title', 'node_id', 'workflow_run_id']:
            if field in event:
                metadata[field] = event.get(field, '')

        # Add outputs and status for node_finished events
        if event_name == DifyEvent.NODE_FINISHED:
            if 'outputs' in event:
                metadata['outputs'] = event.get('outputs', {})
            if 'status' in event:
                metadata['status'] = event.get('status', '')

        return metadata

    async def _create_node_artifacts(self, task, event, event_queue) -> None:
        """Create artifacts for specific node types."""
        node_type = event.get('node_type', '')
        if node_type not in ['http-request', 'llm', 'variable-aggregator']:
            return

        outputs = event.get('outputs', {})
        title = event.get('title', node_type.capitalize())

        # For HTTP requests, create an artifact with the response
        if node_type == 'http-request' and 'body' in outputs:
            body_text = self._format_http_response(outputs['body'])

            event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    contextId=task.contextId,
                    taskId=task.id,
                    lastChunk=True,
                    artifact=new_text_artifact(
                        name=f'{title}_response',
                        description=f'API response from {title}',
                        text=body_text,
                    ),
                )
            )

        # For LLM nodes, create an artifact with the generated text
        elif node_type == 'llm' and 'text' in outputs:
            node_id = event.get('node_id', '')
            artifact_name = f'llm_response_{node_id[-8:]}'

            # Register this artifact for potential streaming updates
            self.step_artifacts[node_id] = {
                'name': artifact_name,
                'description': f'Generated text from {title}',
            }

            event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    contextId=task.contextId,
                    taskId=task.id,
                    lastChunk=True,
                    artifact=new_text_artifact(
                        name=artifact_name,
                        description=f'Generated text from {title}',
                        text=outputs['text'],
                    ),
                )
            )

    def _format_http_response(self, body: str) -> str:
        """Format HTTP response body, parsing JSON if possible."""
        try:
            json_body = json.loads(body)
            return json.dumps(json_body, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return body

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
