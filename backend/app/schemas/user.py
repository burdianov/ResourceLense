from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserListItem(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str]

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    is_active: bool | None = None
    roles: list[str] | None = None
