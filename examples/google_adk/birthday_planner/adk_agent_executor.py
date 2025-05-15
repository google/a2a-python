import asyncio
import logging

from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any
from uuid import uuid4

import httpx

from google.adk import Runner
from google.adk.agents import LlmAgent, RunConfig
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from pydantic import ConfigDict

from a2a.client import A2AClient
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Artifact,
    FilePart,
    FileWithBytes,
    FileWithUri,
    GetTaskRequest,
    GetTaskSuccessResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    SendMessageSuccessResponse,
    Task,
    TaskQueryParams,
    TaskState,
    TaskStatus,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils import get_text_parts
from a2a.utils.errors import ServerError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

AUTH_TASK_POLLING_DELAY_SECONDS = 0.2


class A2ARunConfig(RunConfig):
    """Custom override of ADK RunConfig to smuggle extra data through the event loop."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )
    current_task_updater: TaskUpdater


class ADKAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Agent."""

    def __init__(self, calendar_agent_url):
        self._agent = LlmAgent(
            model='gemini-2.0-flash-001',
            name='birthday_planner_agent',
            description='An agent that helps manage birthday parties.',
            after_tool_callback=self._handle_auth_required_task,
            instruction="""
    You are an agent that helps plan birthday parties.

    Your job as a party planner is to act as a sounding board and idea generator for
    users who are planning a birthday party.

    You should provide suggestions on, or encourage the user to provide details on:
    - Venues
    - Time of day, day of week to hold the party
    - Age-appropriate activities
    - Themes for the party

    You can delegate tasks to a separate Calendar Agent that can help manage the user's calendar.
    """,
            tools=[self.message_calendar_agent],
        )
        self.calendar_agent_endpoint = calendar_agent_url
        self.runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _run_agent(
        self,
        session_id,
        new_message: types.Content,
        task_updater: TaskUpdater,
    ) -> AsyncGenerator[Event]:
        return self.runner.run_async(
            session_id=session_id,
            user_id='self',
            new_message=new_message,
            run_config=A2ARunConfig(current_task_updater=task_updater),
        )

    async def _handle_auth_required_task(
        self,
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: ToolContext,
        tool_response: dict,
    ) -> dict | None:
        """Handle requests that return auth-required."""
        if tool.name != 'message_calendar_agent':
            return None
        if not tool_context.state.get('task_suspended'):
            return None
        dependent_task = Task.model_validate(
            tool_context.state['dependent_task']
        )
        if dependent_task.status.state != TaskState.auth_required:
            return None
        task_updater = self._get_task_updater(tool_context)
        task_updater.update_status(
            dependent_task.status.state, message=dependent_task.status.message
        )
        # This is not a robust solution. We expect that the calendar agent will only
        # ever go from auth-required -> completed. A more robust solution would have
        # more complete state transition handling.
        task = await self._wait_for_dependent_task(dependent_task)
        task_updater.update_status(
            TaskState.working,
            message=task_updater.new_agent_message(
                [Part(TextPart(text='Checking calendar agent output'))]
            ),
        )
        tool_context.state['task_suspended'] = False
        tool_context.state['dependent_task'] = None
        content = []
        if task.artifacts:
            for artifact in task.artifacts:
                content.extend(get_text_parts(artifact.parts))
        return {'response': '\n'.join(content)}

    def _get_task_updater(self, tool_context: ToolContext):
        return tool_context._invocation_context.run_config.current_task_updater

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> AsyncIterable[TaskStatus | Artifact]:
        session_id = self._upsert_session(
            session_id,
        ).id
        async for event in self._run_agent(
            session_id, new_message, task_updater
        ):
            logger.debug('Received ADK event: %s', event)
            if event.is_final_response():
                response = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('Yielding final response: %s', response)
                task_updater.add_artifact(response)
                task_updater.complete()
                break
            if calls := event.get_function_calls():
                for call in calls:
                    # Provide an update on what we're doing.
                    if call.name == 'message_calendar_agent':
                        task_updater.update_status(
                            TaskState.working,
                            message=task_updater.new_agent_message(
                                [
                                    Part(
                                        root=TextPart(
                                            text='Messaging the calendar agent'
                                        )
                                    )
                                ]
                            ),
                        )
            elif not event.get_function_calls():
                logger.debug('Yielding update response')
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts)
                    ),
                )
            else:
                logger.debug('Skipping event')

    async def _wait_for_dependent_task(self, dependent_task: Task):
        async with httpx.AsyncClient() as client:
            # Subscribe would be good. We'll poll instead.
            a2a_client = A2AClient(
                httpx_client=client, url=self.calendar_agent_endpoint
            )
            # We want to wait until the task is in a terminal state.
            while not self._is_task_complete(dependent_task):
                await asyncio.sleep(AUTH_TASK_POLLING_DELAY_SECONDS)
                response = await a2a_client.get_task(
                    GetTaskRequest(params=TaskQueryParams(id=dependent_task.id))
                )
                if not isinstance(response.root, GetTaskSuccessResponse):
                    logger.debug('Getting dependent task failed: %s', response)
                    # In a real scenario, may want to feed this response back to
                    # the agent loop to decide what to do. We'll just fail the
                    # task.
                    raise Exception('Getting dependent task failed')
                dependent_task = response.root.result
            return dependent_task

    def _is_task_complete(self, task: Task) -> bool:
        return task.status.state == TaskState.completed

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until either complete or the task is suspended.
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            updater.submit()
        updater.start_work()
        await self._process_request(
            types.UserContent(
                parts=convert_a2a_parts_to_genai(context.message.parts),
            ),
            context.context_id,
            updater,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())

    def _upsert_session(self, session_id: str):
        return self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        ) or self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )

    async def message_calendar_agent(
        self, message: str, tool_context: ToolContext
    ):
        """Send a message to the calendar agent."""
        # We take an overly simplistic approach to the A2A state machine:
        # - All requests to the calendar agent use the current session ID as the context ID.
        # - If the last response from the calendar agent (in this session) produced a non-terminal
        #   task state, the request references that task.
        request = SendMessageRequest(
            params=MessageSendParams(
                message=Message(
                    contextId=tool_context._invocation_context.session.id,
                    taskId=tool_context.state.get('task_id'),
                    messageId=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=message))],
                )
            )
        )
        response = await self._send_agent_message(request)
        logger.debug('[A2A Client] Received response: %s', response)
        task_id = None
        content = []
        if isinstance(response.root, SendMessageSuccessResponse):
            if isinstance(response.root.result, Task):
                task = response.root.result
                if task.artifacts:
                    for artifact in task.artifacts:
                        content.extend(get_text_parts(artifact.parts))
                if not content:
                    content.extend(get_text_parts(task.status.message.parts))
                # Ideally should be "is terminal state"
                if task.status.state != TaskState.completed:
                    task_id = task.id
                if task.status.state == TaskState.auth_required:
                    tool_context.state['task_suspended'] = True
                    tool_context.state['dependent_task'] = task.model_dump()
            else:
                content.extend(get_text_parts(response.root.result.parts))
        tool_context.state['task_id'] = task_id
        # Just turn it all into a string.
        return {'response': '\n'.join(content)}

    async def _send_agent_message(self, request: SendMessageRequest):
        async with httpx.AsyncClient() as client:
            calendar_agent_client = A2AClient(
                httpx_client=client, url=self.calendar_agent_endpoint
            )
            return await calendar_agent_client.send_message(request)

    async def _get_agent_task(self, task_id) -> Task:
        async with httpx.AsyncClient() as client:
            a2a_client = A2AClient(
                httpx_client=client, url=self.calendar_agent_endpoint
            )
            await a2a_client.get_task({'id': task_id})


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    """Convert a list of A2A Part types into a list of Google Gen AI Part types."""
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Convert a single A2A Part type into a Google Gen AI Part type."""
    part = part.root
    if isinstance(part, TextPart):
        return types.Part(text=part.text)
    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            return types.Part(
                file_data=types.FileData(
                    file_uri=part.file.uri, mime_type=part.file.mime_type
                )
            )
        if isinstance(part.file, FileWithBytes):
            return types.Part(
                inline_data=types.Blob(
                    data=part.file.bytes, mime_type=part.file.mime_type
                )
            )
        raise ValueError(f'Unsupported file type: {type(part.file)}')
    raise ValueError(f'Unsupported part type: {type(part)}')


def convert_genai_parts_to_a2a(parts: list[types.Part]) -> list[Part]:
    """Convert a list of Google Gen AI Part types into a list of A2A Part types."""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data)
    ]


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Convert a single Google Gen AI Part type into an A2A Part type."""
    if part.text:
        return TextPart(text=part.text)
    if part.file_data:
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    if part.inline_data:
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    raise ValueError(f'Unsupported part type: {part}')
