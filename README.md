# A2A Python SDK

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![PyPI - Version](https://img.shields.io/pypi/v/a2a-sdk)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/a2a-sdk)

<!-- markdownlint-disable no-inline-html -->

<html>
   <h2 align="center">
   <img src="https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/docs/assets/a2a-logo-black.svg" width="256" alt="A2A Logo"/>
   </h2>
   <h3 align="center">A Python library that helps run agentic applications as A2AServers following the <a href="https://google.github.io/A2A">Agent2Agent (A2A) Protocol</a>.</h3>
</html>

<!-- markdownlint-enable no-inline-html -->

## Installation

You can install the A2A SDK using either `uv` or `pip`.

## Prerequisites

- Python 3.10+
- `uv` (optional, but recommended) or `pip`

### Using `uv`

When you're working within a uv project or a virtual environment managed by uv, the preferred way to add packages is using uv add.

```bash
uv add a2a-sdk
```

### Using `pip`

If you prefer to use pip, the standard Python package installer, you can install `a2a-sdk` as follows

```bash
pip install a2a-sdk
```

## Examples

### [Helloworld Example](https://github.com/google-a2a/a2a-samples/tree/main/samples/python/agents/helloworld)

1. Run Remote Agent

   ```bash
   git clone https://github.com/google-a2a/a2a-samples.git
   cd a2a-samples/samples/python/agents/helloworld
   uv run .
   ```

2. In another terminal, run the client

   ```bash
   cd a2a-samples/samples/python/agents/helloworld
   uv run test_client.py
   ```

You can also find more Python samples [here](https://github.com/google-a2a/a2a-samples/tree/main/samples/python) and JavaScript samples [here](https://github.com/google-a2a/a2a-samples/tree/main/samples/js).

### Blog Post Generation Agent Example

This example demonstrates an agent capable of generating blog posts using the Gemini API.

#### Prerequisites

1.  **Install Dependencies**:
    Ensure you have all necessary dependencies installed. If you've followed the main installation for `a2a-sdk`, you might also need `python-dotenv` and `google-generativeai`:
    ```bash
    pip install python-dotenv google-generativeai
    ```
    (Note: `google-generativeai` should already be installed if previous steps were followed for this agent, but `python-dotenv` is likely new for this example).

2.  **Set up Gemini API Key**:
    - Create a `.env` file in the root of this repository by copying the `.env.example` file:
      ```bash
      cp .env.example .env
      ```
    - Edit the `.env` file and replace `"your_actual_google_gemini_api_key_here"` with your actual Gemini API key.
      ```
      GEMINI_API_KEY="your_actual_api_key_here"
      ```

#### Running the Example

1.  Navigate to the `examples` directory (if you are not already there):
    ```bash
    cd examples
    ```
2.  Run the script:
    ```bash
    python run_blog_generator.py
    ```
    The script will:
    - Generate a blog topic based on predefined keywords.
    - Generate an outline for the topic.
    - Write content for each section of the outline.
    - Assemble the full blog post.
    - Print the final blog post to the console and save it to `generated_blog_post.md` in the `examples` directory (where the script is run).

#### How it Works

The `run_blog_generator.py` script uses the `ExampleAgent` located in `src/a2a/example_agent/agent.py`. This agent has been configured with capabilities to:
- `generate_blog_topic`: Creates a topic.
- `generate_blog_outline`: Structures the blog post.
- `write_blog_section`: Writes content for each section using the Gemini API.
- `assemble_blog_post`: Compiles the sections into a final blog post.

The agent reads the `GEMINI_API_KEY` from the environment variables (loaded from the `.env` file located in the project root or the `examples/` directory).

*Note: The `ExampleAgent` currently uses placeholder classes for some core A2A SDK components (`Agent`, `AgentCapability`, etc.) as they were not found directly within the SDK during development of this example. These placeholders would ideally be replaced by actual SDK components.*

## License

This project is licensed under the terms of the [Apache 2.0 License](https://raw.githubusercontent.com/google-a2a/a2a-python/refs/heads/main/LICENSE).

## Contributing

See [CONTRIBUTING.md](https://github.com/google-a2a/a2a-python/blob/main/CONTRIBUTING.md) for contribution guidelines.
