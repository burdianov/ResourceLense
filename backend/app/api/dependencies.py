from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, status
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

    if access_token is None:
        raise credentials_exception

    try:
        payload = decode_access_token(
            token=access_token,
            secret_key=settings.jwt_secret_key,
        )

        subject = payload.get("sub")

        if subject is None:
            raise credentials_exception

        user_id = int(subject)

    except InvalidTokenError, ValueError:
        raise credentials_exception

    statement = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )

    user = db.scalar(statement)

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_permission(
    permission_name: str,
) -> Callable[..., User]:
    def permission_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_permissions = {
            permission.name
            for role in current_user.roles
            for permission in role.permissions
        }

        if permission_name not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_dependency
