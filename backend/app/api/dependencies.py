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


def collect_permissions(user: User) -> set[str]:
    return {
        permission.name
        for role in user.roles
        for permission in role.permissions
    }


def _load_user(db: Session, user_id: int) -> User | None:
    statement = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles).selectinload(Role.permissions))
    )

    return db.scalar(statement)


def get_optional_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the signed-in user, or None when there is no valid session.

    Returns None for a missing, malformed, expired or revoked token, and for a
    user that has since been deactivated. Roles and permissions are re-read
    from the database on every request, so authorisation changes apply
    immediately rather than waiting for the token to expire.
    """
    if access_token is None:
        return None

    try:
        payload = decode_access_token(
            token=access_token,
            secret_key=settings.jwt_secret_key,
        )

        subject = payload.get("sub")

        if subject is None:
            return None

        user_id = int(subject)
    except (InvalidTokenError, ValueError):
        return None

    user = _load_user(db, user_id)

    if user is None or not user.is_active:
        return None

    token_version = payload.get("ver")

    if not isinstance(token_version, int) or token_version != user.token_version:
        return None

    return user


def get_current_user(
    current_user: User | None = Depends(get_optional_current_user),
) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return current_user


def require_permission(
    permission_name: str,
) -> Callable[..., User]:
    def permission_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if permission_name not in collect_permissions(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_dependency


def require_any_permission(
    *permission_names: str,
) -> Callable[..., User]:
    """Allow the request when the user holds at least one of the permissions.

    Used for shared reference data, for example listing roles from both the
    user administration and the role administration screens.
    """
    required = frozenset(permission_names)

    def permission_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not collect_permissions(current_user) & required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_dependency
