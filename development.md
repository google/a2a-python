# Development

## Type generation from spec

<!-- TODO replace spec.json with the public url so we always get the latest version-->

```bash
uv run datamodel-codegen --input ./spec.json --input-file-type jsonschema --output ./src/a2a/types.py --target-python-version 3.10 --output-model-type pydantic_v2.BaseModel --disable-timestamp --use-schema-description --use-union-operator --use-field-description --use-default --use-default-kwarg --use-one-literal-as-default --class-name A2A --use-standard-collections
```
