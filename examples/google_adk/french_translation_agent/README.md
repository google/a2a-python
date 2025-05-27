# ADK French Translation Agent with A2A Client

This example shows how to create an A2A Server that uses an ADK-based Agent for translating text to French. This agent uses a Gemini model directly.

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- A `GOOGLE_API_KEY` for using Gemini models.

## Running the example

1.  Create the `.env` file in this directory with your API Key:

    ```bash
    echo "GOOGLE_API_KEY=your_google_api_key_here" > .env
    ```

2.  Start the server:

    ```sh
    uv run . --port 10011
    ```
    (The default port is 10011, but you can change it with the `--port` option).

3.  You can test this agent by sending requests to its endpoint (e.g., `http://localhost:10011`) using an A2A client or by having an orchestrator agent delegate tasks to it. The agent's ID for delegation is `french_translator`.

    Example interaction (conceptual):
    - User (to orchestrator): "Translate 'Hello, how are you?' to French."
    - Orchestrator: Delegates to `french_translator`.
    - French Translator (this agent): Returns "Bonjour, comment ça va ?"
