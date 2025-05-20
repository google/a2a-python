# Build Agents using A2A SDK
----
> *⚠️ DISCLAIMER: THIS DEMO IS INTENDED FOR DEMONSTRATION PURPOSES ONLY. IT IS NOT INTENDED FOR USE IN A PRODUCTION ENVIRONMENT.*  

> *⚠️ Important: A2A is a work in progress (WIP) thus, in the near future there might be changes that are different from what demonstrated here.*
----

This document describes a web application demonstrating the integration of Google's Agent to Agent (A2A), Agent Development Kit (ADK) for multi-agent orchestration with Model Context Protocol (MCP) clients. The application features a host agent coordinating tasks between remote agents that interact with various MCP servers to fulfill user requests.

### Architecture

The application utilizes a multi-agent architecture where a host agent delegates tasks to remote agents (Airbnb and Weather) based on the user's query. These agents then interact with corresponding MCP servers.

![architecture](assets/A2A_multi_agent.png)

### App UI
![screenshot](assets/screenshot.png)


## Setup and Deployment

### Prerequisites

Before running the application locally, ensure you have the following installed:

1. **Node.js:** Required to run the Airbnb MCP server (if testing its functionality locally).
2. **uv:** The Python package management tool used in this project. Follow the installation guide: [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
3. **python 3.13** Python 3.13 is required to run a2a-sdk 
4. **set up .env** 


- create .env file in `airbnb_agent` and `weather_agent`folder with the following content
```bash
GOOGLE_API_KEY="your_api_key_here" 
```

- create .env file in `host_agent/adk_agent`folder with the following content:

```bash
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT="your project"
GOOGLE_CLOUD_LOCATION=us-central1
AIR_AGENT_URL=http://localhost:10002
WEA_AGENT_URL=http://localhost:10001
```

## Install SDK
Go to `a2a-mcp-app` folder in terminal:
```bash
uv sync
```


## 1. Run Airbnb server

Run Remote server

```bash
cd airbnb_agent
uv run .
```

## 2. Run Weather server
Open a new terminal, go to `a2a-mcp-app` folder run the server

```bash
cd weather_agent
uv run .
```

## 3. Run Host Agent
Open a new terminal, go to `a2a-mcp-app` folder run the server

```bash
cd host_agent
uv run app.py
```


## 4. Test at the UI

Here are example questions:

- "Tell me about weather in LA, CA"  

- "Please find a room in LA, CA, June 20-25, 2025, two adults"

## References
- https://github.com/google/a2a-python
- https://codelabs.developers.google.com/intro-a2a-purchasing-concierge#1
- https://google.github.io/adk-docs/
