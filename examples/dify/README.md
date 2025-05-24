# Dify Integration Example

This example demonstrates an A2A agent that integrates with the Dify API.

## Features

- Makes HTTP POST requests to the Dify workflow API endpoint
- Demonstrates how to wrap an external API in an A2A agent
- Includes both regular and streaming response handling

## Getting started

1. Start the server

   ```bash
   python __main__.py
   ```

2. Run the test client in another terminal

   ```bash
   python test_client.py
   ```

## API Details

The agent makes requests to the following Dify endpoint:

- URL: `http://192.168.8.41:8080/v1/workflows/run`
- Method: POST
- Headers:
  - Authorization: Bearer app-wd1WTcAnHPLqRjTAm4QmswI9
  - Content-Type: application/json
- Request Body:
  ```json
  {
    "inputs": {},
    "response_mode": "blocking",
    "user": "test@kingsware.cn"
  }
  ```
