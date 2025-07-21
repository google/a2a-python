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

    This implementation overrides __setattr__ to allow setting fields
    using their camelCase alias for backward compatibility.
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
    # The type hint is now corrected to be `ClassVar[<optional_type>]`.
    _alias_to_field_name_map: ClassVar[dict[str, str] | None] = None

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow setting attributes via their camelCase alias.

        This is overridden to provide backward compatibility for code that
        sets model fields using aliases after initialization.
        """
        # Build the alias-to-name mapping on first use and cache it.
        if self.__class__._alias_to_field_name_map is None:  # noqa: SLF001
            # Using a lock or other mechanism could make this more thread-safe
            # for highly concurrent applications, but this is fine for most cases.
            self.__class__._alias_to_field_name_map = {  # noqa: SLF001
                field.alias: field_name
                for field_name, field in self.model_fields.items()
                if field.alias is not None
            }

        # If the attribute name is a known alias, redirect the assignment
        # to the actual (snake_case) field name.
        field_name = self.__class__._alias_to_field_name_map.get(name)  # noqa: SLF001
        if field_name:
            # Use the actual field name for the assignment
            super().__setattr__(field_name, value)
        else:
            # Otherwise, perform a standard attribute assignment
            super().__setattr__(name, value)
