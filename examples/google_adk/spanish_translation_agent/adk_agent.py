import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

MODEL_GPT_3_5_TURBO = "openai/gpt-3.5-turbo"

async def create_spanish_translation_agent() -> LlmAgent:
    """Constructs the ADK Spanish Translation agent using LiteLLM."""
    # LiteLLM uses environment variables for API keys (e.g., OPENAI_API_KEY).
    # Ensure the required API key for the chosen model is set.
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY environment variable not set. LiteLLM may fail if using an OpenAI model.")

    return LlmAgent(
        model=LiteLlm(model=MODEL_GPT_3_5_TURBO),
        name='spanish_translation_agent_adk',
        description='An agent that translates text to Spanish.',
        instruction="""You are a translation assistant. The user will provide text.
Translate the provided text into Spanish.
Only return the translated Spanish text. Do not include any other commentary or explanations.
Example: If the user provides "Hello, how are you?", you should return "Hola, ¿cómo estás?"
""",
        tools=[], # No specific tools are needed as the LLM performs the translation directly.
    )
