from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    permissions: list[str]
    user_count: int
    is_protected: bool


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = None


class PermissionResponse(BaseModel):
    id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)
