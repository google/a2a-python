"""
AI Foundry Agent Executor for A2A framework.
Adapted from ADK agent executor pattern to work with Azure AI Foundry agents.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, List
from collections.abc import AsyncGenerator

from foundry_agent import FoundryCalendarAgent

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


class FoundryAgentExecutor(AgentExecutor):
    """
    An AgentExecutor that runs Azure AI Foundry-based agents.
    Adapted from the ADK agent executor pattern.
    """
    
    def __init__(self, card: AgentCard):
        self._card = card
        self._foundry_agent: Optional[FoundryCalendarAgent] = None
        self._active_threads: Dict[str, str] = {}  # context_id -> thread_id mapping
        
    async def _get_or_create_agent(self) -> FoundryCalendarAgent:
        """Get or create the Foundry calendar agent."""
        if not self._foundry_agent:
            from foundry_agent import create_foundry_calendar_agent
            self._foundry_agent = await create_foundry_calendar_agent()
        return self._foundry_agent
    
    async def _get_or_create_thread(self, context_id: str) -> str:
        """Get or create a thread for the given context."""
        if context_id not in self._active_threads:
            agent = await self._get_or_create_agent()
            thread = await agent.create_thread()
            self._active_threads[context_id] = thread.id
            logger.info(f"Created new thread {thread.id} for context {context_id}")
        
        return self._active_threads[context_id]
    
    async def _process_request(
        self,
        message_parts: List[Part],
        context_id: str,
        task_updater: TaskUpdater,
    ) -> None:
        """Process a user request through the Foundry agent."""
        try:
            # Convert A2A parts to text message
            user_message = self._convert_parts_to_text(message_parts)
            
            # Get agent and thread
            agent = await self._get_or_create_agent()
            thread_id = await self._get_or_create_thread(context_id)
            
            # Update status
            task_updater.update_status(
                TaskState.working,
                message=new_agent_text_message(
                    "Processing your request...", context_id=context_id
                ),
            )
            
            # Run the conversation
            responses = await agent.run_conversation(thread_id, user_message)
            
            # Send responses back
            for response in responses:
                task_updater.update_status(
                    TaskState.working,
                    message=new_agent_text_message(
                        response, context_id=context_id
                    ),
                )
            
            # Mark as complete
            final_message = responses[-1] if responses else "Task completed."
            task_updater.complete(
                message=new_agent_text_message(
                    final_message, context_id=context_id
                )
            )
            
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            task_updater.failed(
                message=new_agent_text_message(
                    f"Error: {str(e)}", context_id=context_id
                )
            )
    
    def _convert_parts_to_text(self, parts: List[Part]) -> str:
        """Convert A2A message parts to a text string."""
        text_parts = []
        
        for part in parts:
            part = part.root
            if isinstance(part, TextPart):
                text_parts.append(part.text)
            elif isinstance(part, FilePart):
                # For demo purposes, just indicate file presence
                if isinstance(part.file, FileWithUri):
                    text_parts.append(f"[File: {part.file.uri}]")
                elif isinstance(part.file, FileWithBytes):
                    text_parts.append(f"[File: {len(part.file.bytes)} bytes]")
            else:
                logger.warning(f"Unsupported part type: {type(part)}")
        
        return " ".join(text_parts)
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        """Execute the agent request."""
        logger.info(f"Executing request for context: {context.context_id}")
        
        # Create task updater
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        
        # Notify task submission
        if not context.current_task:
            updater.submit()
        
        # Start working
        updater.start_work()
        
        # Process the request
        await self._process_request(
            context.message.parts,
            context.context_id,
            updater,
        )
        
        logger.debug(f"Foundry agent execution completed for {context.context_id}")
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        """Cancel the ongoing execution."""
        logger.info(f"Cancelling execution for context: {context.context_id}")
        
        # For now, just log cancellation
        # In a full implementation, you might want to:
        # 1. Cancel any ongoing API calls
        # 2. Clean up resources
        # 3. Notify the task store
        
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        updater.fail(
            message=new_agent_text_message(
                "Task cancelled by user", context_id=context.context_id
            )
        )
    
    async def cleanup(self):
        """Clean up resources."""
        if self._foundry_agent:
            await self._foundry_agent.cleanup_agent()
            self._foundry_agent = None
        self._active_threads.clear()
        logger.info("Foundry agent executor cleaned up")


def create_foundry_agent_executor(card: AgentCard) -> FoundryAgentExecutor:
    """Factory function to create a Foundry agent executor."""
    return FoundryAgentExecutor(card)
