# ADK MCP Brave Search Agent with A2A Client

This example shows how to create an A2A Server that uses an ADK-based Agent that performs Brave Searches via the Model Context Protocol (MCP).

## Prerequisites

- Python 3.13 or higher
- [UV](https://docs.astral.sh/uv/)
- A Brave Search API Key (required for the Brave Search MCP server)

## Running the example

1. Create the `.env` file with your API Key in this directory:

   ```bash
   echo "BRAVE_API_KEY=your_brave_api_key_here" > .env
   ```
   (Ensure your `GOOGLE_API_KEY` is also present if other examples or parts of the ADK setup require it, though this specific agent only needs `BRAVE_API_KEY`.)


2. Start the server

   ```sh
   uv run .
   ```

3. Run the test client

   ```sh
   uv run test_client.py
   ```

   Or the CLI client:
   ```sh
   uv run cli_client.py --query "your search query"
