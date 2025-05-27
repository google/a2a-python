# ADK Spanish Translation Agent with A2A Client (using LiteLLM)

This example shows how to create an A2A Server that uses an ADK-based Agent for translating text to Spanish. This agent utilizes LiteLLM to connect to an underlying LLM (e.g., OpenAI's GPT models).

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- An API Key for the LLM provider you intend to use via LiteLLM (e.g., `OPENAI_API_KEY` for OpenAI models).

## Running the example

1.  Create the `.env` file in this directory with your API Key:

    For example, if using an OpenAI model:
    ```bash
    echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
    ```
    Ensure the model specified in `adk_agent.py` (e.g., `openai/gpt-3.5-turbo`) corresponds to the API key you provide.

2.  Start the server:

    ```sh
    uv run . --port 10010 
    ```
    (The default port is 10010, but you can change it with the `--port` option).

3.  You can test this agent by sending requests to its endpoint (e.g., `http://localhost:10010`) using an A2A client or by having an orchestrator agent delegate tasks to it. The agent's ID for delegation is `spanish_translator`.

    Example interaction (conceptual):
    - User (to orchestrator): "Translate 'Hello, how are you?' to Spanish."
    - Orchestrator: Delegates to `spanish_translator`.
    - Spanish Translator (this agent): Returns "Hola, ¿cómo estás?"
