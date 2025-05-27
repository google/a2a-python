"""
AI Foundry Agent implementation with calendar capabilities.
Adapted from the ADK agent pattern to work with Azure AI Foundry.
"""
import os
import time
import datetime
import asyncio
import logging
import json
from typing import Optional, Dict, Any, List

from azure.ai.agents import AgentsClient
from azure.ai.agents.models import Agent, ThreadMessage, ThreadRun, AgentThread, ToolOutput
from azure.ai.agents.operations import ThreadsOperations
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

logger = logging.getLogger(__name__)


class FoundryCalendarAgent:
    """
    AI Foundry Agent with calendar management capabilities.
    This class adapts the ADK calendar agent pattern for Azure AI Foundry.
    """
    
    def __init__(self):
        self.endpoint = os.environ["AZURE_AI_FOUNDRY_PROJECT_ENDPOINT"]
        self.credential = DefaultAzureCredential()
        self.agent: Optional[Agent] = None
        self.threads: Dict[str, str] = {}  # thread_id -> thread_id mapping
        
    def _get_client(self) -> AgentsClient:
        """Get a new AgentsClient instance for use in context managers."""
        return AgentsClient(
            endpoint=self.endpoint,
            credential=self.credential,
        )
        
    async def create_agent(self) -> Agent:
        """Create the AI Foundry agent with calendar instructions."""
        if self.agent:
            return self.agent
            
        with self._get_client() as client:
            self.agent = client.create_agent(
                model=os.environ["AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"],
                name="foundry-calendar-agent",
                instructions=self._get_calendar_instructions(),
                tools=self._get_calendar_tools()
            )
            logger.info(f"Created AI Foundry agent: {self.agent.id}")
            return self.agent
    
    def _get_calendar_instructions(self) -> str:
        """Get the agent instructions adapted from ADK calendar agent."""
        return f"""
You are an intelligent calendar management agent powered by Azure AI Foundry.

Your capabilities include:
- Checking calendar availability
- Managing calendar events
- Providing schedule insights
- Helping with time management

Key guidelines:
- If not specified, assume the user wants information about their 'primary' calendar
- Use well-formed RFC3339 timestamps for all date/time operations
- Be helpful and proactive in suggesting optimal meeting times
- Always confirm important scheduling actions with the user

Current date and time: {datetime.datetime.now().isoformat()}

When users ask about availability, scheduling, or calendar management, use your calendar tools to provide accurate and helpful responses.
"""
    
    def _get_calendar_tools(self) -> List[Dict[str, Any]]:
        """Define calendar tools for the agent (simulated for demo)."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check if a time slot is available in the user's calendar",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_time": {
                                "type": "string",
                                "description": "Start time in RFC3339 format"
                            },
                            "end_time": {
                                "type": "string", 
                                "description": "End time in RFC3339 format"
                            },
                            "calendar_id": {
                                "type": "string",
                                "description": "Calendar ID (defaults to 'primary')",
                                "default": "primary"
                            }
                        },
                        "required": ["start_time", "end_time"]
                    }
                }
            },
            {
                "type": "function", 
                "function": {
                    "name": "get_upcoming_events",
                    "description": "Get upcoming events from the user's calendar",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of events to return",
                                "default": 10
                            },
                            "time_range_hours": {
                                "type": "integer", 
                                "description": "Number of hours from now to check",
                                "default": 24
                            }
                        }
                    }
                }
            }
        ]
    
    async def create_thread(self, thread_id: Optional[str] = None) -> AgentThread:
        """Create or retrieve a conversation thread."""
        if thread_id and thread_id in self.threads:
            # Return thread info - we'll need to get it fresh each time
            pass
            
        with self._get_client() as client:
            thread = client.threads.create()
            self.threads[thread.id] = thread.id
            logger.info(f"Created thread: {thread.id}")
            return thread
    
    async def send_message(self, thread_id: str, content: str, role: str = "user") -> ThreadMessage:
        """Send a message to the conversation thread."""
        with self._get_client() as client:
            message = client.messages.create(
                thread_id=thread_id,
                role=role,
                content=content
            )
            logger.info(f"Created message in thread {thread_id}: {message.id}")
            return message
    
    async def run_conversation(self, thread_id: str, user_message: str) -> List[str]:
        """Run a complete conversation cycle with the agent."""
        if not self.agent:
            await self.create_agent()
            
        # Send user message
        await self.send_message(thread_id, user_message)
        
        # Create and run the agent
        with self._get_client() as client:
            run = client.runs.create(
                thread_id=thread_id,
                agent_id=self.agent.id
            )
            
            # Poll until completion
            max_iterations = 30  # Prevent infinite loops
            iterations = 0
            
            while run.status in ["queued", "in_progress", "requires_action"] and iterations < max_iterations:
                iterations += 1
                time.sleep(1)
                run = client.runs.get(thread_id=thread_id, run_id=run.id)
                logger.debug(f"Run status: {run.status} (iteration {iterations})")
                
                if run.status == "failed":
                    logger.error(f"Run failed during polling: {run.last_error}")
                    break
                
                # Handle tool calls if needed
                if run.status == "requires_action":
                    try:
                        await self._handle_tool_calls(run, thread_id)
                        # Get updated run status after tool submission
                        run = client.runs.get(thread_id=thread_id, run_id=run.id)
                    except Exception as e:
                        logger.error(f"Error handling tool calls: {e}")
                        # If tool handling fails, mark the run as failed
                        return [f"Error handling tool calls: {str(e)}"]
            
            if run.status == "failed":
                logger.error(f"Run failed: {run.last_error}")
                return [f"Error: {run.last_error}"]
                
            if iterations >= max_iterations:
                logger.error(f"Run timed out after {max_iterations} iterations")
                return ["Error: Request timed out"]
            
            # Get response messages
            messages = client.messages.list(
                thread_id=thread_id, 
                order=ListSortOrder.DESCENDING
            )
            
            responses = []
            for msg in messages:
                if msg.role == "assistant" and msg.text_messages:
                    for text_msg in msg.text_messages:
                        responses.append(text_msg.text.value)
                    break  # Only get the latest assistant response
                    
            return responses if responses else ["No response received"]
    
    async def _handle_tool_calls(self, run: ThreadRun, thread_id: str):
        """Handle tool calls during agent execution."""
        logger.info("Handling tool calls (simulated for demo)")
        
        if not hasattr(run, 'required_action') or not run.required_action:
            logger.warning("No required action found in run")
            return
            
        required_action = run.required_action
        if not hasattr(required_action, 'submit_tool_outputs') or not required_action.submit_tool_outputs:
            logger.warning("No tool outputs required")
            return
            
        try:
            tool_calls = required_action.submit_tool_outputs.tool_calls
            if not tool_calls:
                logger.warning("No tool calls found in required action")
                return
                
            tool_outputs = []
            
            # Process each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = tool_call.function.arguments
                
                logger.info(f"Processing tool call: {function_name} with args: {arguments}")
                logger.debug(f"Tool call ID: {tool_call.id}")
                
                # Simulate calendar tool responses
                if function_name == "check_availability":
                    output = {
                        "available": True,
                        "message": "The requested time slot appears to be available."
                    }
                elif function_name == "get_upcoming_events":
                    output = {
                        "events": [
                            {
                                "title": "Team Meeting",
                                "start": "2025-05-27T14:00:00Z",
                                "end": "2025-05-27T15:00:00Z"
                            },
                            {
                                "title": "Project Review",
                                "start": "2025-05-27T16:00:00Z", 
                                "end": "2025-05-27T17:00:00Z"
                            }
                        ]
                    }
                else:
                    output = {"error": f"Unknown function: {function_name}"}
                
                # Ensure we have a valid tool_call_id
                if not hasattr(tool_call, 'id') or not tool_call.id:
                    logger.error(f"Tool call missing ID: {tool_call}")
                    continue
                    
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(output)  # Ensure output is JSON string
                })
            
            if not tool_outputs:
                logger.error("No valid tool outputs generated")
                return
                
            logger.debug(f"Tool outputs to submit: {tool_outputs}")
            
        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            logger.error(f"Required action structure: {required_action}")
            raise
        
        # Submit the tool outputs
        with self._get_client() as client:
            try:
                # Create tool outputs in the expected format
                formatted_outputs = []
                for output in tool_outputs:
                    formatted_outputs.append(ToolOutput(
                        tool_call_id=output["tool_call_id"],
                        output=output["output"]
                    ))
                
                logger.debug(f"Submitting formatted tool outputs: {formatted_outputs}")
                
                client.runs.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=formatted_outputs
                )
                logger.info(f"Submitted {len(formatted_outputs)} tool outputs")
            except Exception as e:
                logger.error(f"Failed to submit tool outputs: {e}")
                logger.error(f"Raw tool outputs structure: {tool_outputs}")
                # Try submitting without ToolOutput wrapper as fallback
                try:
                    logger.info("Trying fallback submission with raw dict format")
                    client.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    logger.info(f"Fallback submission successful")
                except Exception as e2:
                    logger.error(f"Fallback submission also failed: {e2}")
                    raise e
        
    async def cleanup_agent(self):
        """Clean up the agent resources."""
        if self.agent:
            with self._get_client() as client:
                client.delete_agent(self.agent.id)
                logger.info(f"Deleted agent: {self.agent.id}")
                self.agent = None


async def create_foundry_calendar_agent() -> FoundryCalendarAgent:
    """Factory function to create and initialize a Foundry calendar agent."""
    agent = FoundryCalendarAgent()
    await agent.create_agent()
    return agent


# Example usage for testing
async def demo_agent_interaction():
    """Demo function showing how to use the Foundry calendar agent."""
    agent = await create_foundry_calendar_agent()
    
    try:
        # Create a conversation thread
        thread = await agent.create_thread()
        
        # Example interactions
        test_messages = [
            "Hello! Can you help me with my calendar?",
            "Am I free tomorrow from 2pm to 3pm?",
            "What meetings do I have coming up today?"
        ]
        
        for message in test_messages:
            print(f"\nUser: {message}")
            responses = await agent.run_conversation(thread.id, message)
            for response in responses:
                print(f"Assistant: {response}")
                
    finally:
        await agent.cleanup_agent()


if __name__ == "__main__":
    asyncio.run(demo_agent_interaction())
