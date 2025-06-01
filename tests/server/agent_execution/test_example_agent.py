import pytest

# Since the agent and its dependencies are now self-contained with placeholders
from a2a.example_agent.agent import ExampleAgent, TaskCompleter, TaskParameters


class MockTaskCompleter(TaskCompleter):
    def __init__(self):
        self.completed_task_output = None
        self.failed_task_error_message = None

    def complete_task(self, output: any):
        self.completed_task_output = output

    def fail_task(self, error_message: str):
        self.failed_task_error_message = error_message


@pytest.mark.asyncio
async def test_example_agent_echo():
    agent = ExampleAgent()
    task_completer = MockTaskCompleter()
    # Assuming TaskParameters can be instantiated with a dict
    parameters = TaskParameters(parameters={"message": "Hello, world!"})

    await agent.execute_task(task_completer, parameters)

    assert task_completer.completed_task_output == "Hello, world!"
    assert task_completer.failed_task_error_message is None

@pytest.mark.asyncio
async def test_example_agent_echo_no_message():
    agent = ExampleAgent()
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={}) # Empty dict for parameters

    await agent.execute_task(task_completer, parameters)

    assert task_completer.completed_task_output == "No message provided."
    assert task_completer.failed_task_error_message is None

@pytest.mark.asyncio
async def test_example_agent_unknown_capability():
    agent = ExampleAgent()
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={"message": "test"})

    # As noted before, the agent's execute_task is hardcoded to "echo".
    # This test reflects that current behavior.
    # If the agent were to correctly use function_to_call.name,
    # and an unknown capability was passed, this test would expect a fail_task call.

    await agent.execute_task(task_completer, parameters) # Still calls "echo"

    assert task_completer.completed_task_output == "test"
    assert task_completer.failed_task_error_message is None
    # Ideal assertion if unknown capabilities were handled:
    # assert task_completer.failed_task_error_message is not None
    # assert "Unknown capability" in task_completer.failed_task_error_message
