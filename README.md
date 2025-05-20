# A2A Python SDK

A Python library that helps run agentic applications as A2AServers following the [Agent2Agent (A2A) Protocol](https://google.github.io/A2A/).

## Installation

You can install the A2A SDK using either `uv` or `pip`.

## Prerequisites

- Python 3.13+
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

### [Helloworld Example](https://github.com/google/a2a-python/tree/main/examples/helloworld)

1. Run Remote Agent

   ```bash
   cd examples/helloworld
   uv run .
   ```

2. In another terminal, run the client

   ```bash
   uv run test_client.py
   ```

You can also find more examples [here](https://github.com/google/A2A/tree/main/samples/python/agents)

## License

This project is licensed under the terms of the [Apache 2.0 License](https://raw.githubusercontent.com/google/a2a-python/refs/heads/main/LICENSE).

## Contributing

See [CONTRIBUTING.md](https://github.com/google/a2a-python/blob/main/CONTRIBUTING.md) for contribution guidelines.
