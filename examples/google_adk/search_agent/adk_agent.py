from google.adk.agents import LlmAgent
from google.adk.tools import google_search


async def create_search_agent() -> LlmAgent:
    """Constructs the ADK search agent."""
    return LlmAgent(
        model='gemini-2.0-flash',
        name='search_agent_adk',
        description='An agent that can perform Google Searches.',
        instruction="""You are a search assistant. The user will provide a location (e.g., zip code, city name) and a search query. Use the Google Search tool to find relevant information for that location and query. Provide a concise textual answer. If the user provides a zip code or city, prioritize results for that area.
        
        Example: "Find coffee shops near 90210" should trigger a search for "coffee shops 90210".
        Example: "What's the weather in London 12345?" should trigger a search for "weather London 12345".
        """,
        tools=[google_search],
    )
