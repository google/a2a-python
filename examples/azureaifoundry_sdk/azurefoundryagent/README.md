# AI Foundry A2A Demo

A demonstration project showcasing the integration of Azure AI Foundry with the Agent-to-Agent (A2A) framework. This project implements an intelligent calendar management agent with the following capabilities:

## Features

- 🤖 **AI Foundry Integration**: Build intelligent agents using Azure AI Foundry
- 📅 **Calendar Management**: Check schedule availability, get upcoming events
- 🔄 **A2A Framework**: Support agent-to-agent communication and collaboration
- 💬 **Conversation Capabilities**: Natural language processing and multi-turn conversations
- 🛠️ **Tool Integration**: Simulated calendar API tool integration

## Project Structure

```
├── foundry_agent.py           # AI Foundry calendar agent 
├── foundry_agent_executor.py  # A2A framework executor
├── __main__.py                # Main application
├── pyproject.toml             # Project dependencies 
├── test_client.toml           # Test 
└── .env.template              # Environment variables template
```

## Quick Start

### 1. Environment Setup

```bash

# Copy environment variables template
cp .env.template .env

# Edit the .env file and fill in your Azure configuration
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync
```

### 3. Configure Azure AI Foundry

Set the following required environment variables in the `.env` file:

```env
AZURE_AI_FOUNDRY_PROJECT_ENDPOINT=Your Azure AI Foundry Project Endpoint
AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME=Your Azure AI Foundry Deployment Model Name
```

### 4. Run the Demo

Open terminal

```bash
# Start Your Azure AI Foundry Agent
uv run .
```

Open another tag in terminal

```bash
# Test 
uv run test_client.py
```


## Agent Capabilities

### Calendar Management Skills

1. **Check Availability** (`check_availability`)
   - Check schedule arrangements for specific time periods
   - Example: "Am I free tomorrow from 2 PM to 3 PM?"

2. **Get Upcoming Events** (`get_upcoming_events`)
   - Get future calendar events
   - Example: "What meetings do I have today?"

3. **Calendar Management** (`calendar_management`)
   - General calendar management and scheduling assistant
   - Example: "Help me optimize tomorrow's schedule"

### Conversation Examples

```
User: Hello, can you help me manage my calendar?
Agent: Of course! I'm the AI Foundry calendar agent, and I can help you check schedule availability, view upcoming events, and optimize your schedule. What do you need help with?

User: Am I free tomorrow from 2 PM to 3 PM?
Agent: Let me check your availability for tomorrow from 2 PM to 3 PM...
```

## Technical Architecture

### Core Components

1. **FoundryCalendarAgent**: 
   - Core implementation of Azure AI Foundry agent
   - Handles conversation logic and tool calls

2. **FoundryAgentExecutor**:
   - A2A framework executor
   - Handles request routing and state management

3. **A2A Integration**:
   - Agent card definitions
   - Skills and capabilities declarations
   - Message transformation and processing

### Key Features

- **Asynchronous Processing**: Full support for Python asynchronous programming
- **Error Handling**: Complete exception handling and logging
- **State Management**: Session and thread state management
- **Extensibility**: Easy to add new tools and skills
