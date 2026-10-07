"""Project access scope (spec #9).

Users must not automatically see every project: normal users only see
projects they have an active membership for, while admin/super users
bypass project scope entirely. Scope is always enforced server-side;
frontend filtering is never relied upon.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMembership
from app.models.user import User


def is_super_user(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def user_can_access_project(
    current_user: User,
    project_id: int,
    db: Session,
) -> bool:
    """Admin bypasses; everyone else needs an active membership."""
    if is_super_user(current_user):
        return True

    membership = db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == current_user.id,
            ProjectMembership.is_active.is_(True),
        )
    )

    return membership is not None


def visible_project_ids(current_user: User, db: Session) -> list[int] | None:
    """IDs of projects the user may see, or None for unrestricted (admin)."""
    if is_super_user(current_user):
        return None

    return list(
        db.scalars(
            select(ProjectMembership.project_id).where(
                ProjectMembership.user_id == current_user.id,
                ProjectMembership.is_active.is_(True),
            )
        ).all()
    )


def project_by_id(db: Session, project_id: int) -> Project | None:
    return db.scalar(select(Project).where(Project.id == project_id))


def require_visible_project(
    current_user: User,
    project_id: int,
    db: Session,
) -> Project:
    project = project_by_id(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not user_can_access_project(current_user, project_id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    return project
