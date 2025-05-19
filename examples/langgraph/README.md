# LangGraph example

An example LangGraph agent that helps with currency conversion.

## Getting started

1. Create an environment file with your API key:

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   ```

2. Start the server

   ```bash
   uv run .
   ```

3. Run the test client

   ```bash
   uv run test_client.py
   ```
