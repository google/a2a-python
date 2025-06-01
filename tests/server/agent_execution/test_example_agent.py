import pytest
from unittest.mock import patch, AsyncMock
import google.generativeai as genai

# Keep existing imports for ExampleAgent, MockTaskCompleter, TaskParameters (adjust path if necessary)
from a2a.example_agent.agent import ExampleAgent, TaskCompleter, TaskParameters # Ensure this path is correct


class MockTaskCompleter(TaskCompleter): # Already correctly defined from previous content
    def __init__(self):
        self.completed_task_output = None
        self.failed_task_error_message = None

    def complete_task(self, output: any):
        self.completed_task_output = output

    def fail_task(self, error_message: str):
        self.failed_task_error_message = error_message


@pytest.fixture
def agent(monkeypatch):
    # Mock the environment variable for GEMINI_API_KEY
    monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")
    return ExampleAgent()

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel.generate_content_async')
async def test_generate_blog_topic(mock_generate_content, agent):
    task_completer = MockTaskCompleter()
    # Create an AsyncMock for the return value of generate_content_async
    # This AsyncMock needs a 'text' attribute.
    async_mock_response = AsyncMock()
    async_mock_response.text = "AI in Education"
    mock_generate_content.return_value = async_mock_response

    parameters = TaskParameters(parameters={"capability_name": "generate_blog_topic", "keywords": ["AI", "education"]})

    await agent.execute_task(task_completer, parameters)

    assert task_completer.completed_task_output == "AI in Education"
    mock_generate_content.assert_called_once()
    assert "Generate a compelling blog post topic" in mock_generate_content.call_args[0][0]
    assert "AI" in mock_generate_content.call_args[0][0]
    assert "education" in mock_generate_content.call_args[0][0]

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel.generate_content_async')
async def test_generate_blog_outline(mock_generate_content, agent):
    task_completer = MockTaskCompleter()
    async_mock_response = AsyncMock()
    async_mock_response.text = "1. Introduction\n2. Main Point\n3. Conclusion"
    mock_generate_content.return_value = async_mock_response

    parameters = TaskParameters(parameters={"capability_name": "generate_blog_outline", "topic": "AI in Education"})

    await agent.execute_task(task_completer, parameters)

    expected_outline = ["1. Introduction", "2. Main Point", "3. Conclusion"]
    assert task_completer.completed_task_output == expected_outline
    mock_generate_content.assert_called_once()
    assert "Generate a blog post outline" in mock_generate_content.call_args[0][0]
    assert "AI in Education" in mock_generate_content.call_args[0][0]

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel.generate_content_async')
async def test_write_blog_section(mock_generate_content, agent):
    task_completer = MockTaskCompleter()
    async_mock_response = AsyncMock()
    async_mock_response.text = "This is a detailed section about AI."
    mock_generate_content.return_value = async_mock_response

    parameters = TaskParameters(parameters={
        "capability_name": "write_blog_section",
        "section_prompt": "Introduction to AI",
        "model": "gemini-1.5-flash-latest"
    })

    await agent.execute_task(task_completer, parameters)

    assert task_completer.completed_task_output == "This is a detailed section about AI."
    mock_generate_content.assert_called_once()
    assert "Write a detailed blog post section" in mock_generate_content.call_args[0][0]
    assert "Introduction to AI" in mock_generate_content.call_args[0][0]


@pytest.mark.asyncio
async def test_assemble_blog_post(agent): # No API call, so no mock needed here
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={
        "capability_name": "assemble_blog_post",
        "title": "My AI Blog",
        "sections": ["Section 1 content.", "Section 2 content."]
    })

    await agent.execute_task(task_completer, parameters)

    expected_post = "# My AI Blog\n\nSection 1 content.\n\nSection 2 content."
    assert task_completer.completed_task_output == expected_post

@pytest.mark.asyncio
async def test_execute_task_missing_parameters(agent):
    task_completer = MockTaskCompleter()

    # Test generate_blog_topic with missing keywords
    parameters_topic = TaskParameters(parameters={"capability_name": "generate_blog_topic"})
    await agent.execute_task(task_completer, parameters_topic)
    assert "Keywords are required" in task_completer.failed_task_error_message
    task_completer.failed_task_error_message = None # Reset for next check

    # Test generate_blog_outline with missing topic
    parameters_outline = TaskParameters(parameters={"capability_name": "generate_blog_outline"})
    await agent.execute_task(task_completer, parameters_outline)
    assert "A topic is required" in task_completer.failed_task_error_message
    task_completer.failed_task_error_message = None

    # Test write_blog_section with missing section_prompt
    parameters_section = TaskParameters(parameters={"capability_name": "write_blog_section"})
    await agent.execute_task(task_completer, parameters_section)
    assert "A section_prompt is required" in task_completer.failed_task_error_message
    task_completer.failed_task_error_message = None

    # Test assemble_blog_post with missing title
    parameters_assemble_title = TaskParameters(parameters={"capability_name": "assemble_blog_post", "sections": ["test"]})
    await agent.execute_task(task_completer, parameters_assemble_title)
    assert "Title and sections are required" in task_completer.failed_task_error_message
    task_completer.failed_task_error_message = None

    # Test assemble_blog_post with missing sections
    parameters_assemble_sections = TaskParameters(parameters={"capability_name": "assemble_blog_post", "title": "test"})
    await agent.execute_task(task_completer, parameters_assemble_sections)
    assert "Title and sections are required" in task_completer.failed_task_error_message

@pytest.mark.asyncio
async def test_agent_initialization_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError) as excinfo:
        ExampleAgent()
    assert "GEMINI_API_KEY environment variable not set" in str(excinfo.value)

@pytest.mark.asyncio
async def test_example_agent_echo(agent): # Make sure 'agent' fixture is used
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={"capability_name": "echo", "message": "Hello, world!"})
    await agent.execute_task(task_completer, parameters)
    assert task_completer.completed_task_output == "Hello, world!"
    assert task_completer.failed_task_error_message is None

@pytest.mark.asyncio
async def test_example_agent_echo_no_message(agent):
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={"capability_name": "echo"}) # "message" is optional
    await agent.execute_task(task_completer, parameters)
    assert task_completer.completed_task_output == "No message provided."
    assert task_completer.failed_task_error_message is None

@pytest.mark.asyncio
async def test_example_agent_unknown_capability(agent):
    task_completer = MockTaskCompleter()
    parameters = TaskParameters(parameters={"capability_name": "non_existent_capability", "message": "test"})
    await agent.execute_task(task_completer, parameters)
    assert task_completer.failed_task_error_message == "Unknown capability: non_existent_capability"
    assert task_completer.completed_task_output is None
