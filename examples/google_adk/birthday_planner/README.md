# ADK Agent with A2A Client

This example shows how to create an A2A Server that uses an ADK-based Agent that communicates with another agent using A2A.

This agent helps plan birthday parties. It has access to a Calendar Agent that it can delegate calendar-related tasks to. This agent is accessed via A2A.

## Prerequisites

- Python 3.9 or higher
- [UV](https://docs.astral.sh/uv/)
- A Gemini API Key

## Running the example

1. Create the `.env` file with your API Key

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. Run the Calendar Agent. See examples/google_adk/calendar_agent.

3. Run the example

   ```sh
   uv run .
   ```
