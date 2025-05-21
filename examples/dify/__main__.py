from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentAuthentication,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)

from agent_executor import DifyAgentExecutor

if __name__ == "__main__":
    skill = AgentSkill(
        id="dify_api_call",
        name="Call Dify API",
        description="Makes a request to the Dify API endpoint",
        tags=["dify", "api", "workflow"],
        examples=["call dify", "run workflow"],
    )

    agent_card = AgentCard(
        name="Dify Agent",
        description="Agent that wraps Dify API",
        url="http://localhost:8888/",
        version="1.0.0",
        defaultInputModes=["text/plain", "application/json"],
        defaultOutputModes=["text/plain", "application/json"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        authentication=AgentAuthentication(schemes=["public"]),
    )

    request_handler = DefaultRequestHandler(
        agent_executor=DifyAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    import uvicorn

    uvicorn.run(server.build(), host="0.0.0.0", port=8888)
