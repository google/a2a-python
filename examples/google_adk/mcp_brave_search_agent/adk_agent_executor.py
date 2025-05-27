# mypy: ignore-errors
import asyncio
import logging

from collections.abc import AsyncGenerator, AsyncIterable

from adk_agent import create_mcp_brave_search_agent
from google.adk import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Artifact,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TaskStatus,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ADKBraveSearchAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Brave Search Agent via MCP."""

    def __init__(self):
        # Initialize the ADK agent and runner.
        self._agent = asyncio.run(create_mcp_brave_search_agent())
        self.runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _run_agent(
        self,
        session_id: str,
        new_message: types.Content,
        task_updater: TaskUpdater,  # This parameter is not used in this method.
    ) -> AsyncGenerator[Event]:
        """Runs the ADK agent with the given message."""
        return self.runner.run_async(
            session_id=session_id,
            user_id='self',
            new_message=new_message,
        )

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> AsyncIterable[TaskStatus | Artifact]:
        """Processes the incoming request by running the ADK agent."""
        session = await self._upsert_session(
            session_id,
        )
        session_id = session.id
        async for event in self._run_agent(
            session_id,
            new_message,
            task_updater,  # Pass task_updater to _run_agent
        ):
            logger.debug('Received ADK event: %s', event)
            if event.is_final_response():
                # If the ADK agent provides a final response, convert it to A2A artifact and complete the task.
                response = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('Yielding final response: %s', response)
                task_updater.add_artifact(response)
                task_updater.complete()
                break
            if not event.get_function_calls():
                # If it's not a final response and no function calls, it's an interim update.
                logger.debug('Yielding update response')
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts)
                    ),
                )
            else:
                # This agent does not use tools, so function calls are unexpected.
                logger.debug(
                    'Skipping event with function call: %s',
                    event.get_function_calls(),
                )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Executes the agent's logic based on the incoming A2A request."""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
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
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str):
        """Retrieves or creates an ADK session."""
        return await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        ) or await self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[types.Part]:
    """Converts a list of A2A Part objects to a list of Google Gen AI Part objects."""
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> types.Part:
    """Converts a single A2A Part object to a Google Gen AI Part object."""
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
    """Converts a list of Google Gen AI Part objects to a list of A2A Part objects."""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data)
    ]


def convert_genai_part_to_a2a(part: types.Part) -> Part:
    """Converts a single Google Gen AI Part object to an A2A Part object."""
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
