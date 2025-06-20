"""A2A Pydantic Base Model with shared configuration."""

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_snake


class A2ABaseModel(BaseModel):
    """Base model for all A2A types with shared configuration."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def __getattr__(self, name: str) -> Any:  # noqa: D105
        snake = to_snake(name)
        if hasattr(self, snake):
            return getattr(self, snake)
        raise AttributeError(
            f'{type(self).__name__} object has no attribute {name!r}'
        )
