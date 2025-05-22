# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import multiprocessing
import uvicorn
import signal # For graceful shutdown
import time # For process join timeout

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentParameter, AgentCapabilities, ParameterType

# Import the agent executor classes
from examples.multi_agent_system.host_agent import HostAgent
from examples.multi_agent_system.plan_agent import PlanAgent
from examples.multi_agent_system.search_agent import SearchAgent
from examples.multi_agent_system.report_agent import ReportAgent

# Define base URL and ports
BASE_URL = "http://localhost"
HOST_AGENT_PORT = 8000
PLAN_AGENT_PORT = 8001
SEARCH_AGENT_PORT = 8002
REPORT_AGENT_PORT = 8003

# Agent URLs
HOST_AGENT_URL = f"{BASE_URL}:{HOST_AGENT_PORT}"
PLAN_AGENT_URL = f"{BASE_URL}:{PLAN_AGENT_PORT}"
SEARCH_AGENT_URL = f"{BASE_URL}:{SEARCH_AGENT_PORT}"
REPORT_AGENT_URL = f"{BASE_URL}:{REPORT_AGENT_PORT}"

# Agent Cards Definition
# Common parameter for tasks
task_param = AgentParameter(name="task_description", type=ParameterType.TEXT, description="The task to process.")
query_param = AgentParameter(name="search_query", type=ParameterType.TEXT, description="The query to search for.")
data_param = AgentParameter(name="combined_data", type=ParameterType.TEXT, description="Data to include in the report.")


host_agent_card = AgentCard(
    id="host-agent-001", # Unique ID
    name="Host Orchestrator Agent",
    description="Orchestrates planning, searching, and reporting agents.",
    icon_uri="https://storage.googleapis.com/agentsea-public-assets/agent-icons/orchestrator.png", 
    capabilities=AgentCapabilities(skills=[
        AgentSkill(
            id="orchestrate_task_v1", # Unique skill ID
            description="Processes a complex task by coordinating with other agents.",
            parameters=[task_param],
            target_url=f"{HOST_AGENT_URL}/execute", 
        )
    ]),
    trust_level=1, 
    version="0.1.0"
)

plan_agent_card = AgentCard(
    id="plan-agent-001",
    name="Planning Agent",
    description="Generates a plan for a given task.",
    icon_uri="https://storage.googleapis.com/agentsea-public-assets/agent-icons/planner.png",
    capabilities=AgentCapabilities(skills=[
        AgentSkill(
            id="generate_plan_v1",
            description="Creates a step-by-step plan for a task description.",
            parameters=[task_param],
            target_url=f"{PLAN_AGENT_URL}/execute",
        )
    ]),
    trust_level=1,
    version="0.1.0"
)

search_agent_card = AgentCard(
    id="search-agent-001",
    name="Search Agent",
    description="Performs searches based on a query.",
    icon_uri="https://storage.googleapis.com/agentsea-public-assets/agent-icons/search.png",
    capabilities=AgentCapabilities(skills=[
        AgentSkill(
            id="perform_search_v1",
            description="Searches for information based on a query string.",
            parameters=[query_param],
            target_url=f"{SEARCH_AGENT_URL}/execute",
        )
    ]),
    trust_level=1,
    version="0.1.0"
)

report_agent_card = AgentCard(
    id="report-agent-001",
    name="Reporting Agent",
    description="Generates a report from combined data.",
    icon_uri="https://storage.googleapis.com/agentsea-public-assets/agent-icons/reporter.png",
    capabilities=AgentCapabilities(skills=[
        AgentSkill(
            id="generate_report_v1",
            description="Creates a formatted report from input data.",
            parameters=[data_param],
            target_url=f"{REPORT_AGENT_URL}/execute",
        )
    ]),
    trust_level=1,
    version="0.1.0"
)


def run_agent_server(agent_executor_class, agent_card, port, agent_urls_for_host=None):
    """
    Sets up and runs a single agent server.
    agent_urls_for_host is a dict required only for HostAgent.
    """
    print(f"Configuring {agent_card.name} on port {port}...")

    if agent_executor_class == HostAgent:
        if agent_urls_for_host is None:
            raise ValueError("HostAgent requires agent_urls_for_host (plan, search, report URLs)")
        agent_executor = HostAgent(
            plan_agent_url=agent_urls_for_host["plan"],
            search_agent_url=agent_urls_for_host["search"],
            report_agent_url=agent_urls_for_host["report"],
            name=agent_card.name,
        )
    else:
        agent_executor = agent_executor_class(name=agent_card.name) 

    task_store = InMemoryTaskStore()
    # Ensure agent_id is passed to DefaultRequestHandler, as it's required
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
        agent_id=agent_card.id, 
    )
    
    app = A2AStarletteApplication(
        agent_card=agent_card,
        request_handler=request_handler,
        root_path="", 
    )

    # uvicorn.run can be problematic with multiprocessing on some platforms/OS versions
    # especially with signal handling. For simplicity, we'll proceed, but in a production
    # setup, alternatives like gunicorn or running uvicorn programmatically with different
    # loop policies might be needed.
    print(f"Starting {agent_card.name} server on {BASE_URL}:{port}...")
    uvicorn.run(app, host="localhost", port=port, log_level="info") 


# Global list to keep track of processes for signal handling
processes = []

def signal_handler(sig, frame):
    print(f"\nCaught signal {sig}, initiating graceful shutdown...")
    for p_info in processes:
        print(f"Terminating process {p_info['name']} (PID: {p_info['process'].pid})...")
        if p_info['process'].is_alive():
            p_info['process'].terminate() # Send SIGTERM

    # Wait for processes to terminate
    for p_info in processes:
        try:
            p_info['process'].join(timeout=10) # Wait for 10 seconds
            if p_info['process'].is_alive():
                print(f"Process {p_info['name']} (PID: {p_info['process'].pid}) did not terminate gracefully, killing.")
                p_info['process'].kill() # Send SIGKILL
            else:
                print(f"Process {p_info['name']} (PID: {p_info['process'].pid}) terminated.")
        except Exception as e:
            print(f"Error during termination of {p_info['name']}: {e}")
    
    print("All agent processes have been dealt with. Exiting.")
    exit(0)


if __name__ == "__main__":
    print("Starting multi-agent system...")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler) # kill command

    host_agent_sub_urls = {
        "plan": PLAN_AGENT_URL,
        "search": SEARCH_AGENT_URL,
        "report": REPORT_AGENT_URL,
    }

    agents_config = [
        (HostAgent, host_agent_card, HOST_AGENT_PORT, host_agent_sub_urls, "HostAgent"),
        (PlanAgent, plan_agent_card, PLAN_AGENT_PORT, None, "PlanAgent"),
        (SearchAgent, search_agent_card, SEARCH_AGENT_PORT, None, "SearchAgent"),
        (ReportAgent, report_agent_card, REPORT_AGENT_PORT, None, "ReportAgent"),
    ]

    # Clear global processes list before starting new ones
    processes.clear()

    for agent_class, card, port, sub_urls, name_for_logging in agents_config:
        process = multiprocessing.Process(
            target=run_agent_server,
            args=(agent_class, card, port, sub_urls)
        )
        processes.append({"process": process, "name": name_for_logging, "card": card})
        process.start()
        print(f"Launched {card.name} process (PID: {process.pid}).")

    print("All agent servers launched. System is running. Press Ctrl+C to stop.")

    # Keep the main process alive until a signal is received
    try:
        while True:
            time.sleep(1) # Keep main thread alive to handle signals
            # Optionally, check if processes are alive and restart if needed (more complex)
            all_stopped = True
            for p_info in processes:
                if p_info['process'].is_alive():
                    all_stopped = False
                    break
            if all_stopped and processes: # if processes list is not empty and all are stopped
                print("All agent processes seem to have stopped unexpectedly. Exiting main.")
                break
    except KeyboardInterrupt: # Should be caught by signal handler, but as a fallback
        print("KeyboardInterrupt in main loop, initiating shutdown via signal handler logic...")
        signal_handler(signal.SIGINT, None)
    finally:
        # Ensure cleanup if loop exits for reasons other than signals handled by signal_handler
        if any(p_info['process'].is_alive() for p_info in processes):
            print("Main loop exited, ensuring processes are terminated...")
            signal_handler(signal.SIGTERM, None) # Trigger cleanup
        print("Multi-agent system main process finished.")
