# mypy: ignore-errors
# 🐍 Python Standard Library Imports
import asyncio
import logging

# 📚 Standard Library Typing and Collections
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any
from uuid import uuid4 # For generating unique IDs

# 🔩 Third-party Library Imports: Google ADK and Gen AI
from google.adk import Runner # Core ADK component for running agents
from google.adk.agents import LlmAgent, RunConfig # ADK agent and run configuration
from google.adk.artifacts import InMemoryArtifactService # For storing artifacts in memory
from google.adk.events import Event # Represents events during agent execution
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService # For agent memory
from google.adk.sessions import InMemorySessionService, Session # For managing agent sessions
from google.adk.tools import BaseTool, ToolContext # Base for creating tools
from google.genai import types as genai_types # Google Gen AI specific types
from pydantic import ConfigDict # For Pydantic model configuration

# 🚀 A2A SDK Imports: Core components for A2A server and client interaction
from a2a.client import A2AClient # A2A client for interacting with other agents (if needed)
from a2a.server.agent_execution import AgentExecutor, RequestContext # Base class for agent executors and request context
from a2a.server.events.event_queue import EventQueue # For managing event queues
from a2a.server.tasks import TaskUpdater # For updating task status
from a2a.types import ( # A2A specific data types
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
from a2a.utils import get_text_parts # Utility for extracting text from parts
from a2a.utils.errors import ServerError # Custom server error type

# 🏠 Local Application/Library Specific Imports
from adk_agent import create_search_agent # Function to create the ADK search agent instance


# 📝 Initialize logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Set logging level to DEBUG for detailed output


# 🤖 Agent Executor Class Definition
class ADKSearchAgentExecutor(AgentExecutor):
    """
    🔌 An AgentExecutor that runs an ADK-based Search Agent.

    This class acts as a bridge between the A2A server framework and the
    Google ADK (Agent Development Kit). It handles incoming A2A requests,
    translates them into a format understood by the ADK agent, runs the
    ADK agent, and then converts the ADK agent's responses back into
    the A2A format.
    """

    def __init__(self):
        # 🛠️ Initialize the ADK agent instance.
        # `create_search_agent()` is an async function, but since `__init__` must be sync,
        # `asyncio.run()` is used here. This is generally okay for one-off initializations.
        self._agent: LlmAgent = asyncio.run(create_search_agent())

        # 🏃‍♂️ Initialize the ADK Runner.
        # The Runner is the main component for orchestrating the ADK agent's lifecycle.
        # It manages sessions, memory, artifacts, and tool execution.
        self.runner = Runner(
            app_name=self._agent.name,  # Associates runs with this specific agent application
            agent=self._agent,          # The ADK agent instance to run
            artifact_service=InMemoryArtifactService(),  # Stores any generated artifacts (e.g., files) in memory
            session_service=InMemorySessionService(),    # Manages conversation sessions in memory
            memory_service=InMemoryMemoryService(),      # Handles the agent's short-term and long-term memory in memory
        )

    def _run_agent(
        self,
        session_id: str, # The ID of the current conversation session
        new_message: genai_types.Content, # The user's message, converted to Google Gen AI format
        task_updater: TaskUpdater, # A2A TaskUpdater, though not directly used in this ADK call
    ) -> AsyncGenerator[Event, None]: # Returns an async generator of ADK Events
        """
        ▶️ Executes the ADK agent with the given message in the specified session.

        This method calls the ADK Runner's `run_async` method, which handles
        the interaction with the LLM, tool execution, and event generation.
        """
        # `user_id='self'` is a placeholder; in a multi-user system, this would be dynamic.
        return self.runner.run_async(
            session_id=session_id,
            user_id='self', # Identifies the user interacting with the agent
            new_message=new_message, # The input message for the agent
            # `run_config` could be used to pass additional parameters if needed
        )

    async def _process_request(
        self,
        new_message: genai_types.Content, # The user's message in Google Gen AI format
        session_id: str,                  # The ID for the current session/conversation
        task_updater: TaskUpdater,        # A2A TaskUpdater to send updates and artifacts
    ) -> AsyncIterable[TaskStatus | Artifact]: # Note: This method doesn't directly yield; updates are via TaskUpdater
        """
        🔄 Processes an incoming user message by running the ADK agent and handling its events.

        This method orchestrates the core logic:
        1. Ensures a session exists for the given `session_id`.
        2. Runs the ADK agent using `_run_agent`.
        3. Iterates through the asynchronous stream of `Event` objects from the agent.
        4. Based on the event type, it updates the A2A task status or adds artifacts.
        """
        # 🗂️ Ensure an ADK session exists for this interaction.
        # This will retrieve an existing session or create a new one if needed.
        session = await self._upsert_session(session_id)
        actual_session_id = session.id # Use the ID from the session object

        # 🔁 Iterate over events generated by the ADK agent.
        # `_run_agent` returns an async generator yielding `Event` objects.
        async for event in self._run_agent(
            actual_session_id, new_message, task_updater
        ):
            logger.debug('📬 Received ADK event: %s', event)

            if event.is_final_response():
                # ✅ The agent has produced its final response.
                # Convert the ADK content parts to A2A parts.
                response_parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('🏁 Yielding final response (as artifact): %s', response_parts)
                # Add the final response as an A2A artifact.
                task_updater.add_artifact(response_parts)
                # Mark the A2A task as complete.
                task_updater.complete()
                break # Exit the loop as this is the final event for this request.

            elif not event.get_function_calls() and event.content and event.content.parts:
                # 💬 The agent has produced an intermediate message (not a tool call).
                # This could be a partial response if streaming is supported by the LLM.
                logger.debug('⏳ Yielding intermediate update response')
                # Convert ADK content parts to A2A parts.
                intermediate_parts = convert_genai_parts_to_a2a(event.content.parts)
                # Update the A2A task with the intermediate message.
                task_updater.update_status(
                    TaskState.working, # Keep the task state as 'working'.
                    message=task_updater.new_agent_message(intermediate_parts),
                )
            else:
                # ⚙️ Other event types (e.g., function calls, errors, unknown).
                # ADK's Runner handles function calls internally by invoking the appropriate tool.
                # For this executor, we simply log and skip these events as they don't
                # directly translate to an A2A task update that the client needs to see
                # beyond the LLM's own reporting of tool use (which would come as content).
                logger.debug('⏭️ Skipping event (e.g., function call in progress, or empty content)')

    async def execute(
        self,
        context: RequestContext, # Provides details about the incoming request and task
        event_queue: EventQueue,  # Queue for sending task updates back to the A2A server
    ):
        """
        🚀 Main execution entry point called by the A2A server for an incoming message.

        This method sets up the `TaskUpdater` and then delegates the core processing
        to the `_process_request` method.
        """
        # 🔔 Initialize the TaskUpdater to send status updates and results.
        # `context.task_id` links updates to the specific A2A task.
        # `context.context_id` is used as the session identifier.
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)

        # 🆕 If this is the first message for a new task, submit its initial 'submitted' state.
        if not context.current_task: # current_task would be None for a new task
            updater.submit() # Sends a 'task_submitted' event

        # 🚦 Signal that the agent is starting to work on the task.
        updater.start_work() # Sends a 'task_started_working' event

        # 📨 Convert the A2A message parts to Google Gen AI `Content` format
        # and then process the request.
        # The `context.message.parts` contains the user's input.
        # `context.context_id` is used as the `session_id` for the ADK agent.
        await self._process_request(
            new_message=genai_types.UserContent( # ADK expects a `Content` object
                parts=convert_a2a_parts_to_genai(context.message.parts),
            ),
            session_id=context.context_id, # Use A2A context_id as ADK session_id
            task_updater=updater,
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """
        🛑 Handles task cancellation requests.

        This example agent does not implement cancellation logic.
        Attempting to cancel a task will result in an `UnsupportedOperationError`.
        """
        # For a real implementation, this might involve signaling the ADK runner
        # or managing internal state to stop processing.
        raise ServerError(error=UnsupportedOperationError(message="Cancellation is not supported by this agent."))

    async def _upsert_session(self, session_id: str) -> Session:
        """
        🗂️ Gets an existing ADK session or creates a new one if it doesn't exist ("upsert").

        ADK agents are typically stateful within a session. This method ensures that
        each A2A `context_id` (which represents a conversation or task chain) maps
        to a persistent ADK session.
        """
        # Try to retrieve an existing session.
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )
        if session:
            return session
        # If no session exists, create a new one.
        return await self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )


# ↔️ Data Conversion Utilities: A2A <-> Google Gen AI

def convert_a2a_parts_to_genai(parts: list[Part]) -> list[genai_types.Part]:
    """
    🔄 Converts a list of A2A `Part` objects to a list of Google Gen AI `Part` objects.
    This is used to prepare user messages for the ADK agent.
    """
    return [convert_a2a_part_to_genai(part) for part in parts]


def convert_a2a_part_to_genai(part: Part) -> genai_types.Part:
    """
    🔄 Converts a single A2A `Part` object to a Google Gen AI `Part` object.
    Handles `TextPart` and `FilePart` (with URI or bytes).
    """
    actual_part = part.root # A2A `Part` is a discriminated union, `root` holds the actual data.
    if isinstance(actual_part, TextPart):
        # 📄 Convert A2A TextPart to Google Gen AI Text Part
        return genai_types.Part(text=actual_part.text)
    if isinstance(actual_part, FilePart):
        # 📁 Convert A2A FilePart
        if isinstance(actual_part.file, FileWithUri):
            # 🔗 File identified by URI
            return genai_types.Part(
                file_data=genai_types.FileData(
                    file_uri=actual_part.file.uri,
                    mime_type=actual_part.file.mime_type,
                )
            )
        if isinstance(actual_part.file, FileWithBytes):
            # 💾 File content as raw bytes, converted to Google Gen AI Blob
            return genai_types.Part(
                inline_data=genai_types.Blob(
                    data=actual_part.file.bytes,
                    mime_type=actual_part.file.mime_type,
                )
            )
        # Should not be reached if A2A types are used correctly
        raise ValueError(f'Unsupported A2A file type within FilePart: {type(actual_part.file)}')
    # Should not be reached if A2A types are used correctly
    raise ValueError(f'Unsupported A2A part type for Gen AI conversion: {type(actual_part)}')


def convert_genai_parts_to_a2a(parts: list[genai_types.Part]) -> list[Part]:
    """
    🔄 Converts a list of Google Gen AI `Part` objects to a list of A2A `Part` objects.
    This is used to process responses from the ADK agent.
    Filters out any parts that don't have recognized content.
    """
    return [
        convert_genai_part_to_a2a(part)
        for part in parts
        # Ensure the Gen AI part has content we can convert
        if (part.text or part.file_data or part.inline_data)
    ]


def convert_genai_part_to_a2a(part: genai_types.Part) -> Part:
    """
    🔄 Converts a single Google Gen AI `Part` object to an A2A `Part` object.
    Handles text, file data (URI), and inline data (bytes).
    """
    if part.text:
        # 📄 Convert Google Gen AI Text Part to A2A TextPart
        return TextPart(text=part.text)
    if part.file_data:
        # 🔗 Convert Google Gen AI FileData (URI) to A2A FilePart with FileWithUri
        return FilePart(
            file=FileWithUri(
                uri=part.file_data.file_uri,
                mime_type=part.file_data.mime_type,
            )
        )
    if part.inline_data:
        # 💾 Convert Google Gen AI InlineData (Blob) to A2A FilePart with FileWithBytes
        # Note: A2A `Part` is a discriminated union, so we wrap FilePart in `Part(root=...)`
        return Part(
            root=FilePart(
                file=FileWithBytes(
                    bytes=part.inline_data.data,
                    mime_type=part.inline_data.mime_type,
                )
            )
        )
    # This should ideally not be reached if parts are pre-filtered in the calling function.
    raise ValueError(f'Unsupported Google Gen AI part type for A2A conversion (empty or unknown): {part}')
