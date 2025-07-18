from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class A2ABaseModel(BaseModel):
    """Base class for shared behavior across A2A data models.

    Provides a common configuration (e.g., alias-based population) and
    serves as the foundation for future extensions or shared utilities.
    """

    model_config = ConfigDict(
        # SEE: https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.populate_by_name
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        alias_generator=to_camel,
    )
