from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import require_any_permission, require_permission
from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import PROTECTED_ROLE_NAMES, Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate


router = APIRouter(prefix="/roles", tags=["roles"])


def _normalize_name(name: str) -> str:
    return name.strip().lower()


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None

    cleaned = description.strip()

    return cleaned or None


def load_role(db: Session, role_id: int) -> Role | None:
    statement = (
        select(Role)
        .where(Role.id == role_id)
        .options(
            selectinload(Role.permissions),
            selectinload(Role.users),
        )
    )

    return db.scalar(statement)


def resolve_permissions(db: Session, names: list[str]) -> list[Permission]:
    if not names:
        return []

    permissions = list(
        db.scalars(select(Permission).where(Permission.name.in_(names))).all()
    )

    missing = set(names) - {permission.name for permission in permissions}

    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Unknown permissions: " + ", ".join(sorted(missing))),
        )

    return permissions


def to_response(role: Role) -> RoleResponse:
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=sorted(permission.name for permission in role.permissions),
        user_count=len(role.users),
        is_protected=role.name in PROTECTED_ROLE_NAMES,
    )


@router.get("/", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission("roles.view", "users.view")
    ),
) -> list[RoleResponse]:
    statement = (
        select(Role)
        .options(
            selectinload(Role.permissions),
            selectinload(Role.users),
        )
        .order_by(Role.name)
    )

    return [to_response(role) for role in db.scalars(statement).all()]


@router.post(
    "/",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.create")),
) -> RoleResponse:
    name = _normalize_name(data.name)

    existing = db.scalar(select(Role).where(Role.name == name))

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists",
        )

    role = Role(
        name=name,
        description=_clean_description(data.description),
        permissions=resolve_permissions(db, data.permissions),
    )

    db.add(role)
    db.commit()
    db.refresh(role)

    created = load_role(db, role.id)

    assert created is not None

    return to_response(created)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.edit")),
) -> RoleResponse:
    role = load_role(db, role_id)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role.name in PROTECTED_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The built-in '{role.name}' role is managed by the RBAC seed "
                "script and cannot be modified"
            ),
        )

    if data.name is not None:
        name = _normalize_name(data.name)

        if name != role.name:
            duplicate = db.scalar(select(Role).where(Role.name == name))

            if duplicate is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A role with this name already exists",
                )

            role.name = name

    if "description" in data.model_fields_set:
        role.description = _clean_description(data.description)

    if data.permissions is not None:
        role.permissions = resolve_permissions(db, data.permissions)

    db.commit()

    updated = load_role(db, role_id)

    assert updated is not None

    return to_response(updated)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.delete")),
) -> None:
    role = load_role(db, role_id)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found",
        )

    if role.name in PROTECTED_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The built-in '{role.name}' role cannot be deleted",
        )

    if role.users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"This role is assigned to {len(role.users)} user(s). "
                "Remove it from those users first."
            ),
        )

    db.delete(role)
    db.commit()
