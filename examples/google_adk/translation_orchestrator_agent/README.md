# ADK Translation Orchestrator Agent

This example demonstrates an A2A Server that acts as an orchestrator for translation tasks. It delegates requests to specialized sub-agents for Spanish and French translation.

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- A `GOOGLE_API_KEY` for the orchestrator's own LLM (e.g., Gemini).
- The Spanish Translation Agent (ID: `spanish_translator`) running (e.g., on port 10010).
- The French Translation Agent (ID: `french_translator`) running (e.g., on port 10011).
- API keys for the models used by the sub-agents (e.g., `OPENAI_API_KEY` for the Spanish agent if it uses an OpenAI model via LiteLLM, `GOOGLE_API_KEY` for the French agent if it uses a Gemini model).

## Running the example

1.  Ensure the Spanish and French translation sub-agents are running on their respective ports.
2.  Create the `.env` file in this directory with the `GOOGLE_API_KEY` for the orchestrator:
    ```bash
    echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
    ```
3.  Start the orchestrator server:
    ```sh
    uv run . --port 10012
    ```
    (The default port is 10012).

## How it Works

The orchestrator agent (`translation_orchestrator`) listens for user requests. Based on the user's input (e.g., "Translate 'Hello' to Spanish"), it uses its LLM to:
1.  Identify the text to be translated.
2.  Identify the target language.
3.  Generate a `transfer_to_agent` function call to delegate the task to the appropriate sub-agent:
    - `spanish_translator` for Spanish.
    - `french_translator` for French.

The ADK framework handles the `transfer_to_agent` call, and the client will then interact directly with the chosen sub-agent to receive the translation.

## Testing

You can test this system by creating a CLI client that sends messages to the orchestrator agent's endpoint (e.g., `http://localhost:10012`).

Example CLI interaction:
```
# Assuming a cli_client.py is adapted for the orchestrator
python cli_client.py --query "Translate 'Good morning' to French" --agent_url http://localhost:10012
```
The output should come from the French Translation Agent.
