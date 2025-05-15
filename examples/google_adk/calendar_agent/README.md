# ADK Agent with Authenticated Tools

This example shows how to create an A2A Server that uses an ADK-based Agent that uses Google-authenticated tools.

## Prerequisites

- Python 3.9 or higher
- [UV](https://docs.astral.sh/uv/)
- A Gemini API Key
- A [Google OAuth Client](https://developers.google.com/identity/openid-connect/openid-connect#getcredentials)
  - Configure your OAuth client to handle redirect URLs at `localhost:10007/authenticate`

## Running the example

1. Create the .env file with your API Key and OAuth2.0 Client details

   ```bash
   echo "GOOGLE_API_KEY=your_api_key_here" > .env
   echo "GOOGLE_CLIENT_ID=your_client_id_here" >> .env
   echo "GOOGLE_CLIENT_SECRET=your_client_secret_here" >> .env
   ```

2. Run the example

   ```bash
   uv run .
   ```
