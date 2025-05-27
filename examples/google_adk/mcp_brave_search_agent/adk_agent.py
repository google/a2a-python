import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)


async def create_mcp_brave_search_agent() -> LlmAgent:
    """Constructs the ADK MCP Brave Search agent."""
    brave_api_key = os.getenv('BRAVE_API_KEY')
    if not brave_api_key:
        raise ValueError(
            'BRAVE_API_KEY environment variable not set. This agent requires it.'
        )

    return LlmAgent(
        model='gemini-2.0-flash',
        name='mcp_brave_search_agent_adk',
        description='An agent that can perform Brave Searches via MCP.',
        instruction="""You are a search assistant that uses the Brave Search API. The user will provide a search query. Use the Brave Search tool to find relevant information. Provide a concise textual answer.
        
        Example: "Latest news about AI" should trigger a Brave Search for "Latest news about AI".
        """,
        tools=[
            # Configure the MCPToolset to connect to the Brave Search MCP server.
            # The 'command' and 'args' specify how to run the MCP server executable.
            # The 'env' dictionary passes necessary environment variables to the MCP server.
            MCPToolset(
                connection_params=StdioServerParameters(
                    command='npx',
                    args=[
                        '-y',
                        '@modelcontextprotocol/server-brave-search',
                    ],
                    env={'BRAVE_API_KEY': brave_api_key},
                ),
            )
        ],
    )
