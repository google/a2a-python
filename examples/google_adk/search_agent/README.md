# ADK Search Agent with A2A Client

This example shows how to create an A2A Server that uses an ADK-based Agent that performs Google Searches.

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- A Gemini API Key (required for `gemini-2.0-flash` model and `google_search` tool)

## Running the example

1. Create the `.env` file with your API Key in this directory:

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. Start the server

   ```sh
   uv run .
   ```

3. Run the test client

   ```sh
   uv run test_client.py
