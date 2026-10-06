from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleResponse


router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
) -> list[Role]:
    statement = select(Role).order_by(Role.name)

    return list(db.scalars(statement).all())
