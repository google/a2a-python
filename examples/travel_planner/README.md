# travel planner example
> This is a Python implementation that adheres to the A2A (Assume to Answer) protocol. 
> It is a travel assistant in line with the specifications of the OpenAI model, capable of providing you with travel planning services.  

## Getting started

1. update [config.json](config.json) with your own OpenAI API key etc.
> You need to modify the values corresponding to model_name and base_url.

```json

{
  "model_name":"gemini-2.0-flash",
  "api_key": "API_KEY",
  "base_url": "https://openRouter.ai/api/v1"
}
```
2. Create an environment file with your API key:
> You need to set the value corresponding to API_KEY.

   ```bash
   echo "API_KEY=your_api_key_here" > .env
   ```

3. Install the dependencies
- Execute it in the root directory of the project. 

   ```bash
   pip install .
   ```

4. Start the server
- Execute it in the travel_planner directory of the project. 
- 
    ```bash
    uv run .
    ```

5. Run the test client
- Execute it in the travel_planner directory of the project. 

    ```bash
    uv run loop_client.py
    ```
   

## License

This project is licensed under the terms of the [Apache 2.0 License](/LICENSE).

## Contributing

See [CONTRIBUTING.md](/CONTRIBUTING.md) for contribution guidelines.

