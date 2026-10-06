from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CurrentUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
