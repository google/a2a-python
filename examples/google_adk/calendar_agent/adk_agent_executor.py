import asyncio
import logging

from collections import namedtuple
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlparse

from google.adk import Runner
from google.adk.auth import AuthConfig
from google.adk.events import Event
from google.genai import types

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    FilePart,
    FileWithBytes,
    FileWithUri,
    Part,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from a2a.utils.message import new_agent_text_message


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ADKAuthDetails = namedtuple(
    'ADKAuthDetails',
    ['state', 'uri', 'future', 'auth_config', 'auth_request_function_call_id'],
)

# 1 minute timeout to keep the demo moving.
auth_receive_timeout_seconds = 60


class ADKAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an ADK-based Agent."""

    _awaiting_auth: dict[str, asyncio.Future]

    def __init__(self, runner: Runner, card: AgentCard):
        self.runner = runner
        self._card = card
        self._awaiting_auth = {}
        self._running_sessions = {}

    def _run_agent(
        self, session_id, new_message: types.Content
    ) -> AsyncGenerator[Event, None]:
        return self.runner.run_async(
            session_id=session_id, user_id='self', new_message=new_message
        )

    async def _process_request(
        self,
        new_message: types.Content,
        session_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        session_id = self._upsert_session(
            session_id,
        ).id
        auth_details = None
        async for event in self._run_agent(session_id, new_message):
            # This agent is expected to do one of two things:
            # 1. Ask follow-up questions.
            # 2. Call the calendar tool and interpret the results.
            # So, there are effectively two cases:
            # 1. The agent was able to run to completion.
            # 2. The function call required authorization.
            # Ideally we'd have a way to interpret whether the response is a completion for the
            # task or requires follow-up, but I'm not going to bother just yet.
            if auth_request_function_call := get_auth_request_function_call(
                event
            ):
                # Gather details, then suspend.
                auth_details = self._prepare_auth_request(
                    auth_request_function_call
                )
                logger.debug(
                    'Yielding auth required response: %s', auth_details.uri
                )
                task_updater.update_status(
                    TaskState.auth_required,
                    message=new_agent_text_message(
                        f'Authorization is required to continue. Visit {auth_details.uri}'
                    ),
                )
                # Break out of event handling loop -- no more work will be done until the authorization
                # is received.
                break
            if event.is_final_response():
                parts = convert_genai_parts_to_a2a(event.content.parts)
                logger.debug('Yielding final response: %s', parts)
                task_updater.add_artifact(parts)
                task_updater.complete()
                break
            if not event.get_function_calls():
                logger.debug('Yielding update response')
                task_updater.update_status(
                    TaskState.working,
                    message=task_updater.new_agent_message(
                        convert_genai_parts_to_a2a(event.content.parts),
                    ),
                )
            else:
                logger.debug('Skipping event')

        if auth_details:
            # After auth is received, we can continue processing this request.
            await self._complete_auth_processing(
                session_id, auth_details, task_updater
            )

    def _prepare_auth_request(
        self, auth_request_function_call: types.FunctionCall
    ) -> ADKAuthDetails:
        # Following ADK's authentication documentation:
        # https://google.github.io/adk-docs/tools/authentication/#2-handling-the-interactive-oauthoidc-flow-client-side
        if not (auth_request_function_call_id := auth_request_function_call.id):
            raise ValueError(
                f'Cannot get function call id from function call: {auth_request_function_call}'
            )
        auth_config = get_auth_config(auth_request_function_call)
        if not (auth_config and auth_request_function_call_id):
            raise ValueError(
                f'Cannot get auth config from function call: {auth_request_function_call}'
            )
        oauth2_config = auth_config.exchanged_auth_credential.oauth2
        base_auth_uri = oauth2_config.auth_uri
        if not base_auth_uri:
            raise ValueError(
                f'Cannot get auth uri from auth config: {auth_config}'
            )
        redirect_uri = f'{self._card.url}authenticate'
        oauth2_config.redirect_uri = redirect_uri
        parsed_auth_uri = urlparse(base_auth_uri)
        query_params_dict = parse_qs(parsed_auth_uri.query)
        state_token = query_params_dict['state'][0]
        future = asyncio.get_running_loop().create_future()
        self._awaiting_auth[state_token] = future
        auth_request_uri = base_auth_uri + f'&redirect_uri={redirect_uri}'
        return ADKAuthDetails(
            state=state_token,
            uri=auth_request_uri,
            future=future,
            auth_config=auth_config,
            auth_request_function_call_id=auth_request_function_call_id,
        )

    async def _complete_auth_processing(
        self,
        session_id: str,
        auth_details: ADKAuthDetails,
        task_updater: TaskUpdater,
    ) -> None:
        logger.debug('Waiting for auth event')
        try:
            auth_uri = await asyncio.wait_for(
                auth_details.future, timeout=auth_receive_timeout_seconds
            )
        except TimeoutError:
            logger.debug('Timed out waiting for auth, marking task as failed')
            task_updater.update_status(
                TaskState.failed,
                message=new_agent_text_message(
                    'Timed out waiting for authorization.',
                    context_id=session_id,
                ),
            )
            return
        logger.debug('Auth received, continuing')
        task_updater.update_status(
            TaskState.working,
            message=new_agent_text_message(
                'Auth received, continuing...', context_id=session_id
            ),
        )
        del self._awaiting_auth[auth_details.state]
        oauth2_config = (
            auth_details.auth_config.exchanged_auth_credential.oauth2
        )
        oauth2_config.auth_response_uri = auth_uri
        auth_content = types.UserContent(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=auth_details.auth_request_function_call_id,
                        name='adk_request_credential',
                        response=auth_details.auth_config.model_dump(),
                    ),
                )
            ]
        )
        await self._process_request(auth_content, session_id, task_updater)

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
        logger.debug('[Calendar] execute exiting')

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())

    async def on_auth_callback(self, state: str, uri: str):
        self._awaiting_auth[state].set_result(uri)

    def _upsert_session(self, session_id: str):
        return self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        ) or self.runner.session_service.create_session(
            app_name=self.runner.app_name, user_id='self', session_id=session_id
        )


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


def get_auth_request_function_call(event: Event) -> types.FunctionCall:
    """Get the special auth request function call from the event."""
    if not (event.content and event.content.parts):
        return None
    for part in event.content.parts:
        if (
            part
            and part.function_call
            and part.function_call.name == 'adk_request_credential'
            and event.long_running_tool_ids
            and part.function_call.id in event.long_running_tool_ids
        ):
            return part.function_call
    return None


def get_auth_config(
    auth_request_function_call: types.FunctionCall,
) -> AuthConfig:
    """Extracts the AuthConfig object from the arguments of the auth request function call."""
    if not auth_request_function_call.args or not (
        auth_config := auth_request_function_call.args.get('auth_config')
    ):
        raise ValueError(
            f'Cannot get auth config from function call: {auth_request_function_call}'
        )
    return AuthConfig.model_validate(auth_config)
