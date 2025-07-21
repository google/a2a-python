from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


def to_camel_custom(snake: str) -> str:
    """Convert a snake_case string to camelCase.

    Args:
        snake: The string to convert.

    Returns:
        The converted camelCase string.
    """
    # First, remove any trailing underscores. This is common for names that
    # conflict with Python keywords, like 'in_' or 'from_'.
    if snake.endswith('_'):
        snake = snake.rstrip('_')
    return to_camel(snake)


class A2ABaseModel(BaseModel):
    """Base class for shared behavior across A2A data models.

    Provides a common configuration (e.g., alias-based population) and
    serves as the foundation for future extensions or shared utilities.

    This implementation overrides __setattr__ and __getattr__ to allow
    getting and setting fields using their camelCase alias for backward
    compatibility.
    """

    model_config = ConfigDict(
        # SEE: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.populate_by_name
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        alias_generator=to_camel_custom,
    )

    # Cache for the alias -> field_name mapping.
    # We use a ClassVar so it's created once per class, not per instance.
    _alias_to_field_name_map: ClassVar[dict[str, str] | None] = None

    @classmethod
    def _initialize_alias_map(cls) -> None:
        """Build and cache the alias-to-field-name mapping."""
        if cls._alias_to_field_name_map is None:
            cls._alias_to_field_name_map = {
                field.alias: field_name
                for field_name, field in cls.model_fields.items()
                if field.alias is not None
            }

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting attributes via their camelCase alias."""
        self.__class__._initialize_alias_map()  # noqa: SLF001
        assert self.__class__._alias_to_field_name_map is not None  # noqa: SLF001

        field_name = self.__class__._alias_to_field_name_map.get(name)  # noqa: SLF001
        if field_name:
            # If the name is an alias, set the actual (snake_case) attribute.
            super().__setattr__(field_name, value)
        else:
            # Otherwise, perform a standard attribute assignment.
            super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        """Allow getting attributes via their camelCase alias.

        This method is called as a fallback when the attribute 'name' is
        not found through normal mechanisms.
        """
        self.__class__._initialize_alias_map()  # noqa: SLF001
        # The map must exist at this point, so we can assert it for type checkers
        assert self.__class__._alias_to_field_name_map is not None  # noqa: SLF001

        field_name = self.__class__._alias_to_field_name_map.get(name)  # noqa: SLF001
        if field_name:
            # If the name is an alias, get the actual (snake_case) attribute.
            return getattr(self, field_name)

        # If the name is not a known alias, it's a genuine missing attribute.
        # It is crucial to raise AttributeError to maintain normal Python behavior.
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
