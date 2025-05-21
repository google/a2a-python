import asyncio
import json
import time
import uuid

from pathlib import Path

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
    """Dify Agent wrapper."""

    async def invoke(self, city: str, response_mode: str = 'blocking') -> str:
        """Make HTTP POST request to Dify API in blocking mode."""
        url = 'https://api.dify.ai/v1/workflows/run'
        headers = {
            'Authorization': 'Bearer app-SXqTiCm89mGr2IJhKvwWgR7s',
            'Content-Type': 'application/json',
        }
        payload = {
            'inputs': {'city': city},
            'response_mode': response_mode,
            'user': 'kingstonwen104@gmail.com',
        }

        async with httpx.AsyncClient(timeout=None) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return f'Dify API Response: {response.json()}'
            except httpx.HTTPError as e:
                return f'Error calling Dify API: {str(e)}'

    async def stream(self, city: str, task_id: str):
        """Stream responses from Dify API, filtering out unimportant events."""
        url = 'https://api.dify.ai/v1/workflows/run'
        headers = {
            'Authorization': 'Bearer app-SXqTiCm89mGr2IJhKvwWgR7s',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        payload = {
            'inputs': {'city': city},
            'response_mode': 'streaming',
            'user': 'kingstonwen104@gmail.com',
        }

        # List of low-level events that we want to skip
        SKIP_EVENTS = {'text_chunk', 'ping', 'iteration_next', 'loop_next'}

        # Events that we want to pass through to the client
        IMPORTANT_EVENTS = {
            'workflow_started',
            'workflow_finished',
            'node_started',
            'node_finished',
        }

        # Prepare file for raw SSE results
        timestamp = int(time.time())
        raw_sse_file = f'dify_raw_sse_{timestamp}.json'
        raw_sse_events = []

        # Track current LLM node for text chunks
        current_llm_node_id = None

        async with (
            httpx.AsyncClient(timeout=None) as client,
            client.stream(
                'POST', url, json=payload, headers=headers
            ) as response,
        ):
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith('data: '):
                    try:
                        raw_data = line[6:]
                        data = json.loads(raw_data)

                        # Store raw SSE event
                        raw_sse_events.append(data)

                        event_type = data.get('event')
                        node_data = data.get('data', {})
                        node_type = node_data.get('node_type', '')

                        # Handle text chunks for real-time updates
                        if event_type == 'text_chunk' and 'text' in data.get(
                            'data', {}
                        ):
                            continue

                        # Mark the start of an LLM node to track text chunks
                        if event_type == 'node_started' and node_type == 'llm':
                            current_llm_node_id = node_data.get('id')

                        # Skip other low-level events
                        if event_type in SKIP_EVENTS:
                            continue

                        # Handle workflow_finished event
                        if event_type == 'workflow_finished':
                            # Get the final text output
                            final_text = data.get('data', {}).get('text', '')
                            if not final_text and 'outputs' in data.get(
                                'data', {}
                            ):
                                final_text = (
                                    data.get('data', {})
                                    .get('outputs', {})
                                    .get('text', '')
                                )

                            yield {
                                'event': event_type,
                                'content': final_text,
                                'is_task_complete': True,
                                'require_user_input': False,
                                'data': data.get('data', {}),
                                'workflow_run_id': data.get('workflow_run_id'),
                                'task_id': data.get('task_id'),
                            }
                            break

                        # Process node events with detailed information
                        if event_type in ['node_started', 'node_finished']:
                            title = node_data.get('title', '')
                            status = node_data.get('status', '')
                            node_id = node_data.get('id', '')

                            # Get outputs for node_finished events
                            outputs = {}
                            if event_type == 'node_finished':
                                outputs = node_data.get('outputs', {})

                                # Reset current LLM node when it finishes
                                if (
                                    node_type == 'llm'
                                    and node_id == current_llm_node_id
                                ):
                                    current_llm_node_id = None

                            # Extract meaningful info from the event
                            event_info = f' - {title}' if title else ''
                            if node_type:
                                event_info += f' ({node_type})'
                            if status and event_type == 'node_finished':
                                event_info += f' - {status}'

                            yield {
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
                            continue

                        # Pass through other important events
                        if event_type in IMPORTANT_EVENTS:
                            # Extract meaningful info from the event
                            event_info = ''
                            if 'data' in data and 'title' in data['data']:
                                event_info = f' - {data["data"]["title"]}'

                            yield {
                                'event': event_type,
                                'content': f'{event_type.replace("_", " ").title()}{event_info}',
                                'is_task_complete': False,
                                'require_user_input': False,
                                'data': data.get('data', {}),
                                'workflow_run_id': data.get('workflow_run_id'),
                                'task_id': data.get('task_id'),
                            }

                    except json.JSONDecodeError:
                        continue

            # Save all raw SSE events to file
            with open(raw_sse_file, 'w', encoding='utf-8') as f:
                json.dump(raw_sse_events, f, ensure_ascii=False, indent=2)
            print(f'Raw SSE events saved to {raw_sse_file}')


class DifyAgentExecutor(AgentExecutor):
    """Dify Agent Executor Implementation."""

    def __init__(self):
        self.agent = DifyAgent()
        self.step_artifacts = {}  # Map to store artifacts by node_id

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        city = None

        # Extract city from DataPart if available
        for part in context.message.parts:
            if hasattr(part.root, 'data'):
                data = part.root.data
                if isinstance(data, dict) and 'city' in data:
                    city = data['city']

        # Create new task if not exists
        task = context.current_task
        if not task:
            print('Creating new task')
            task = new_task(context.message)
            event_queue.enqueue_event(task)

        # Send initial working status
        initial_message = new_agent_text_message(
            f'Processing weather request for {city}...', task.contextId, task.id
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

        # Invoke the agent with streaming response
        async for event in self.agent.stream(city, task.id):
            if event['is_task_complete']:
                # Final artifact with complete response
                final_text = event['content']
                event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        contextId=task.contextId,
                        taskId=task.id,
                        lastChunk=True,
                        artifact=new_text_artifact(
                            name='result',
                            description=f'Weather information for {city}',
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
            else:
                event_name = event.get('event', '')
                content = event['content']

                # Create a message with additional metadata
                message = new_agent_text_message(
                    content, task.contextId, task.id
                )

                # Add rich metadata based on event type
                metadata = {
                    'dify_event': event_name,
                }

                # Add node-specific information if available
                if 'node_type' in event:
                    metadata['node_type'] = event.get('node_type', '')
                if 'title' in event:
                    metadata['title'] = event.get('title', '')
                if 'node_id' in event:
                    metadata['node_id'] = event.get('node_id', '')
                if 'workflow_run_id' in event:
                    metadata['workflow_run_id'] = event.get(
                        'workflow_run_id', ''
                    )

                # Add outputs and status for node_finished events
                if event_name == 'node_finished':
                    if 'outputs' in event:
                        metadata['outputs'] = event.get('outputs', {})
                    if 'status' in event:
                        metadata['status'] = event.get('status', '')

                    # For specific node types, create artifacts with their outputs
                    node_type = event.get('node_type', '')
                    if node_type in [
                        'http-request',
                        'llm',
                        'variable-aggregator',
                    ]:
                        outputs = event.get('outputs', {})
                        title = event.get('title', node_type.capitalize())

                        # For HTTP requests, create an artifact with the response
                        if node_type == 'http-request' and 'body' in outputs:
                            try:
                                # Try to parse JSON for better formatting
                                json_body = json.loads(outputs['body'])
                                body_text = json.dumps(
                                    json_body, indent=2, ensure_ascii=False
                                )
                            except:
                                body_text = outputs['body']

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

                # Add metadata to the message
                message.metadata = metadata

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

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise Exception('cancel not supported')
