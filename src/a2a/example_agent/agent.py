# Placeholder classes - replace with actual imports from a2a.sdk when available
class Agent:
    def __init__(self, capabilities):
        self.capabilities = capabilities

class AgentCapability:
    def __init__(self, name, description, parameters):
        self.name = name
        self.description = description
        self.parameters = parameters

class TaskCompleter:
    def complete_task(self, output):
        raise NotImplementedError

    def fail_task(self, error_message):
        raise NotImplementedError

class TaskParameters:
    def __init__(self, parameters):
        self.parameters = parameters

    def get(self, key, default=None):
        return self.parameters.get(key, default)

# End of placeholder classes

from a2a.types import AgentCapabilities  # Assuming AgentCapabilities is available
# from a2a.server.task_queue import TaskParameters # Assuming TaskParameters is available


class ExampleAgent(Agent):
    """An example agent that echoes back the input."""

    def __init__(self):
        super().__init__(
            capabilities=AgentCapabilities(
                initial_prompt="You are an example agent.",
                capabilities=[
                    AgentCapability(
                        name="echo",
                        description="Echoes back the input.",
                        parameters={
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "The message to echo.",
                                },
                            },
                            "required": ["message"],
                        },
                    )
                ],
            )
        )

    async def execute_task(
        self,
        task_completer: TaskCompleter,
        parameters: TaskParameters,
        # TODO: Add type hint for function_to_call
        # function_to_call: FunctionToCallBase,
    ):
        """Executes the task by echoing back the input."""
        # TODO: Fix this once the type hint for function_to_call is added
        # capability_name = function_to_call.name
        capability_name = "echo"  # Assuming echo for now
        if capability_name == "echo":
            message = parameters.get("message", "No message provided.")
            # In a real scenario, task_completer would be an object
            # that can signal completion or failure of the task.
            # For this example, we'll assume it has methods like complete_task.
            if hasattr(task_completer, 'complete_task') and callable(task_completer.complete_task):
                task_completer.complete_task(output=message)
            else:
                # Handle the case where task_completer is not as expected,
                # perhaps log or raise an error specific to this example's setup.
                print(f"Debug: Task output would be: {message}")
        else:
            if hasattr(task_completer, 'fail_task') and callable(task_completer.fail_task):
                task_completer.fail_task(error_message=f"Unknown capability: {capability_name}")
            else:
                print(f"Debug: Task would fail with error: Unknown capability: {capability_name}")
