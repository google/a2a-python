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

### [Helloworld Example](https://github.com/google/a2a-samples/tree/main/samples/helloworld)

1. Run Remote Agent

   ```bash
   git clone https://github.com/google-a2a/a2a-samples.git
   cd samples/helloworld
   uv run .
   ```

2. In another terminal, run the client

   ```bash
   uv run test_client.py
   ```

You can also find more examples [here](https://github.com/google-a2a/A2A/tree/main/samples/python/agents)

## License

This project is licensed under the terms of the [Apache 2.0 License](https://raw.githubusercontent.com/google-a2a/a2a-python/refs/heads/main/LICENSE).

## Contributing

See [CONTRIBUTING.md](https://github.com/google-a2a/a2a-python/blob/main/CONTRIBUTING.md) for contribution guidelines.
