from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest
from app.services.auth import authenticate_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    user = authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        subject=user.id,
        secret_key=settings.jwt_secret_key,
        expires_minutes=settings.access_token_expire_minutes,
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=settings.environment == "production",
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=CurrentUserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    roles = sorted(role.name for role in current_user.roles)

    permissions = sorted(
        {
            permission.name
            for role in current_user.roles
            for permission in role.permissions
        }
    )

    return CurrentUserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=roles,
        permissions=permissions,
    )
