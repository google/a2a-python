# mypy: ignore-errors
import asyncio
import logging

from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any
from uuid import uuid4

from google.adk import Runner
from google.adk.agents import LlmAgent, RunConfig
from google.adk.artifacts import InMemoryArtifactService
from google.adk.events import Event
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
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

from adk_agent import create_translation_orchestrator_agent


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ADKTranslationOrchestratorAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Translation Orchestrator Agent."""

    def __init__(self):
        # Initialize the ADK agent and runner for the orchestrator.
        self._agent = asyncio.run(create_translation_orchestrator_agent())
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
        new_message: genai_types.Content,
        task_updater: TaskUpdater, # This parameter is not used in this method.
    ) -> AsyncGenerator[Event, None]:
        """Runs the ADK orchestrator agent with the given message."""
        return self.runner.run_async(
            session_id=session_id,
            user_id='self',
            new_message=new_message,
        )

    async def _process_request(
        self,
        new_message: genai_types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> AsyncIterable[TaskStatus | Artifact]:
        """Processes the incoming request by running the ADK orchestrator agent."""
        session = await self._upsert_session(
            session_id,
        )
        session_id = session.id
        async for event in self._run_agent(
            session_id, new_message, task_updater # Pass task_updater to _run_agent
        ):
            logger.debug('Orchestrator Received ADK event: %s', event)
            
            if event.is_final_response():
                # The final response from the orchestrator's LLM, which should be the translated text or an error.
                final_parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('Orchestrator LLM final content parts: %s', final_parts)

                task_updater.add_artifact(parts=final_parts)
                task_updater.complete()
                logger.info("Orchestrator task completed with final parts added as artifact.")
                break
            elif event.get_function_calls():
                # Log when the LLM generates a function call (delegation to sub-agent).
                logger.info(f"Orchestrator LLM generated function call: {event.get_function_calls()}")
            elif event.content and event.content.parts:
                # Interim response from the orchestrator's LLM.
                logger.debug('Orchestrator LLM interim response parts: %s', event.content.parts)
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts)
                    ),
                )
            else:
                logger.debug('Orchestrator skipping event: %s', event)


    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Executes the orchestrator agent's logic based on the incoming A2A request."""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            updater.submit()
        updater.start_work()
        
        # Convert the initial user message parts to GenAI format for the orchestrator agent.
        initial_user_message_parts = convert_a2a_parts_to_genai(context.message.parts)
        
        await self._process_request(
            genai_types.UserContent(parts=initial_user_message_parts),
            context.context_id,
            updater,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise ServerError(error=UnsupportedOperationError())

    async def _upsert_session(self, session_id: str):
        """Retrieves or creates an ADK session for the orchestrator."""
        return await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        ) or await self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )


def convert_a2a_parts_to_genai(parts: list[Part]) -> list[genai_types.Part]:
    """Converts a list of A2A Part objects to a list of Google GenAI Part objects."""
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> genai_types.Part:
    """Converts a single A2A Part object to a Google GenAI Part object."""
    part = part.root
    if isinstance(part, TextPart):
        return genai_types.Part(text=part.text)
    if isinstance(part, FilePart):
        if isinstance(part.file, FileWithUri):
            return genai_types.Part(
                file_data=genai_types.FileData(
                    file_uri=part.file.uri, mime_type=part.file.mime_type
                )
            )
        if isinstance(part.file, FileWithBytes):
            return genai_types.Part(
                inline_data=genai_types.Blob(
                    data=part.file.bytes, mime_type=part.file.mime_type
                )
            )
        raise ValueError(f'Unsupported file type: {type(part.file)}')
    raise ValueError(f'Unsupported part type: {type(part)}')


def convert_genai_parts_to_a2a(parts: list[genai_types.Part]) -> list[Part]:
    """Converts a list of Google GenAI Part objects to a list of A2A Part objects."""
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        if (part.text or part.file_data or part.inline_data)
    ]


def convert_genai_part_to_a2a(part: genai_types.Part) -> Part:
    """Converts a single Google GenAI Part object to an A2A Part object."""
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
