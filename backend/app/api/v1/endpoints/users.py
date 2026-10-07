from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import require_permission
from app.core.security import hash_password
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserListItem,
    UserPasswordReset,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserListItem])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
) -> list[UserListItem]:
    statement = (
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.full_name, User.email)
    )

    users = db.scalars(statement).all()

    return [
        UserListItem(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            roles=sorted(role.name for role in user.roles),
        )
        for user in users
    ]


@router.post(
    "/",
    response_model=UserListItem,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.create")),
) -> UserListItem:
    email = str(data.email).strip().lower()

    existing_user = db.scalar(select(User).where(User.email == email))

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    roles: list[Role] = []

    if data.roles:
        roles = list(db.scalars(select(Role).where(Role.name.in_(data.roles))).all())

        found_role_names = {role.name for role in roles}
        missing_roles = set(data.roles) - found_role_names

        if missing_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("Unknown roles: " + ", ".join(sorted(missing_roles))),
            )

    user = User(
        email=email,
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
        is_active=True,
        roles=roles,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=sorted(role.name for role in user.roles),
    )


@router.patch(
    "/{user_id}",
    response_model=UserListItem,
)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.edit")),
) -> UserListItem:
    user = db.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if data.full_name is not None:
        user.full_name = data.full_name.strip()

    if data.is_active is not None:
        if user.id == current_user.id and not data.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )

        user.is_active = data.is_active

    if data.roles is not None:
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own roles",
            )

        roles = list(db.scalars(select(Role).where(Role.name.in_(data.roles))).all())

        found_role_names = {role.name for role in roles}
        missing_roles = set(data.roles) - found_role_names

        if missing_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=("Unknown roles: " + ", ".join(sorted(missing_roles))),
            )

        user.roles = roles

    db.commit()
    db.refresh(user)

    return UserListItem(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=sorted(role.name for role in user.roles),
    )


@router.put(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reset_user_password(
    user_id: int,
    data: UserPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.edit")),
) -> None:
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = hash_password(data.password)

    # Invalidate any session the user already had open.
    user.token_version += 1

    db.commit()
