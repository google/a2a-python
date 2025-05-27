# Development

## Type generation from spec

```bash
uv run datamodel-codegen \
  --url https://raw.githubusercontent.com/google-a2a/A2A/refs/heads/main/specification/json/a2a.json \
  --input-file-type jsonschema \
  --output ./src/a2a/types.py \
  --target-python-version 3.10 \
  --output-model-type pydantic_v2.BaseModel \
  --disable-timestamp \
  --use-schema-description \
  --use-union-operator \
  --use-field-description \
  --use-default \
  --use-default-kwarg \
  --use-one-literal-as-default \
  --class-name A2A \
  --use-standard-collections
```
