# import httpx

# from typing_extensions import override

# from a2a.server.agent_execution import AgentExecutor, RequestContext
# from a2a.server.events import EventQueue
# from a2a.utils import new_agent_text_message


# class DifyAgent:
#     """Dify Agent wrapper."""

#     async def invoke(self, city: str, response_mode: str = 'blocking') -> str:
#         """Make HTTP POST request to Dify API in blocking mode."""
#         url = 'https://api.dify.ai/v1/workflows/run'
#         headers = {
#             'Authorization': 'Bearer app-SXqTiCm89mGr2IJhKvwWgR7s',
#             'Content-Type': 'application/json',
#         }
#         payload = {
#             'inputs': {'city': city},
#             'response_mode': response_mode,
#             'user': 'kingstonwen104@gmail.com',
#         }

#         async with httpx.AsyncClient(timeout=None) as client:
#             try:
#                 response = await client.post(url, json=payload, headers=headers)
#                 response.raise_for_status()
#                 return f"Dify API Response: {response.json()}"
#             except httpx.HTTPError as e:
#                 return f"Error calling Dify API: {str(e)}"


# class DifyAgentExecutor(AgentExecutor):
#     """Dify Agent Executor Implementation."""

#     def __init__(self):
#         self.agent = DifyAgent()

#     @override
#     async def execute(
#         self,
#         context: RequestContext,
#         event_queue: EventQueue,
#     ) -> None:
#         city = None

#         # Extract city from DataPart if available
#         for part in context.message.parts:
#             data = part.root.data
#             city = data['city']

#         print(city)
#         result = await self.agent.invoke(city, 'blocking')
#         event_queue.enqueue_event(new_agent_text_message(result))

#     @override
#     async def cancel(
#         self, context: RequestContext, event_queue: EventQueue
#     ) -> None:
#         raise Exception('cancel not supported')
