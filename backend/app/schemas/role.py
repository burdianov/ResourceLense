from pydantic import BaseModel, ConfigDict


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
