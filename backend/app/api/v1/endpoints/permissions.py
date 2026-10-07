from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.schemas.role import PermissionResponse


router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("roles.view")),
) -> list[Permission]:
    statement = select(Permission).order_by(Permission.name)

    return list(db.scalars(statement).all())
