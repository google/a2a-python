from pydantic import BaseModel, ConfigDict

class A2ABaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )
