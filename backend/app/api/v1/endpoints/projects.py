from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.project import Project, ProjectApprover, ProjectMembership
from app.models.user import User
from app.schemas.project import (
    ProjectApproverCreate,
    ProjectApproverResponse,
    ProjectApproverUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectMembershipCreate,
    ProjectMembershipResponse,
    ProjectMembershipUpdate,
    ProjectUpdate,
)


router = APIRouter(prefix="/projects", tags=["projects"])


def _is_super_user(user: User) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _to_list_item(project: Project) -> ProjectListItem:
    return ProjectListItem(
        id=project.id,
        code=project.code,
        name=project.name,
        status=project.status,
        created_by_id=project.created_by_id,
        created_at=project.created_at,
    )


def _to_detail(project: Project) -> ProjectDetail:
    return ProjectDetail(
        id=project.id,
        code=project.code,
        name=project.name,
        client_name=project.client_name,
        location=project.location,
        description=project.description,
        status=project.status,
        tender_start_date=project.tender_start_date,
        tender_submission_date=project.tender_submission_date,
        expected_award_date=project.expected_award_date,
        planned_start_date=project.planned_start_date,
        planned_end_date=project.planned_end_date,
        actual_start_date=project.actual_start_date,
        actual_end_date=project.actual_end_date,
        award_probability=project.award_probability,
        archived_at=project.archived_at,
        created_by_id=project.created_by_id,
        updated_by_id=project.updated_by_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def user_can_access_project(
    current_user: User,
    project_id: int,
    db: Session,
) -> bool:
    """Project-scope check. Admin bypasses; everyone else needs membership."""
    if _is_super_user(current_user):
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
    if _is_super_user(current_user):
        return None

    return list(
        db.scalars(
            select(ProjectMembership.project_id).where(
                ProjectMembership.user_id == current_user.id,
                ProjectMembership.is_active.is_(True),
            )
        ).all()
    )


def _project_by_id(db: Session, project_id: int) -> Project | None:
    return db.scalar(select(Project).where(Project.id == project_id))


def _require_visible_project(
    current_user: User,
    project_id: int,
    db: Session,
) -> Project:
    project = _project_by_id(db, project_id)

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


def _clean(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


VALID_PROJECT_STATUSES = {
    "tender",
    "awarded",
    "active",
    "on_hold",
    "completed",
    "lost",
    "cancelled",
}


def _validate_status(value: str) -> str:
    if value not in VALID_PROJECT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown project status {value!r}. "
                f"Valid: {', '.join(sorted(VALID_PROJECT_STATUSES))}"
            ),
        )

    return value


@router.get("/", response_model=list[ProjectListItem])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.view")),
) -> list[ProjectListItem]:
    statement = (
        select(Project)
        .where(Project.archived_at.is_(None))
        .order_by(Project.name, Project.code)
    )

    visible = visible_project_ids(current_user, db)

    if visible is not None:
        if not visible:
            return []

        statement = statement.where(Project.id.in_(visible))

    return [
        _to_list_item(project) for project in db.scalars(statement).all()
    ]


@router.get("/archived", response_model=list[ProjectListItem])
def list_archived_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.view")),
) -> list[ProjectListItem]:
    statement = (
        select(Project)
        .where(Project.archived_at.is_not(None))
        .order_by(Project.name, Project.code)
    )

    visible = visible_project_ids(current_user, db)

    if visible is not None:
        if not visible:
            return []

        statement = statement.where(Project.id.in_(visible))

    return [
        _to_list_item(project) for project in db.scalars(statement).all()
    ]


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.view")),
) -> ProjectDetail:
    project = _require_visible_project(current_user, project_id, db)

    return _to_detail(project)


@router.post(
    "/",
    response_model=ProjectDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.create")),
) -> ProjectDetail:
    code = (data.code or "").strip()
    name = (data.name or "").strip()

    if not code or not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project code and name are required",
        )

    existing = db.scalar(select(Project).where(Project.code == code))

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A project with this code already exists",
        )

    status_value = _validate_status(data.status or "tender")

    if data.award_probability is not None and not (
        0 <= data.award_probability <= 100
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Award probability must be between 0 and 100",
        )

    project = Project(
        code=code,
        name=name,
        client_name=_clean(data.client_name, 255),
        location=_clean(data.location, 255),
        description=_clean(data.description, 2000),
        status=status_value,
        tender_start_date=data.tender_start_date,
        tender_submission_date=data.tender_submission_date,
        expected_award_date=data.expected_award_date,
        planned_start_date=data.planned_start_date,
        planned_end_date=data.planned_end_date,
        actual_start_date=data.actual_start_date,
        actual_end_date=data.actual_end_date,
        award_probability=data.award_probability,
        created_by_id=current_user.id,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return _to_detail(project)


@router.patch("/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.edit")),
) -> ProjectDetail:
    project = _require_visible_project(current_user, project_id, db)

    if data.code is not None:
        code = data.code.strip()

        if code != project.code:
            if not code:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Project code is required",
                )

            duplicate = db.scalar(select(Project).where(Project.code == code))

            if duplicate is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A project with this code already exists",
                )

            project.code = code

    if data.name is not None:
        name = data.name.strip()

        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Project name is required",
            )

        project.name = name

    if "client_name" in data.model_fields_set:
        project.client_name = _clean(data.client_name, 255)

    if "location" in data.model_fields_set:
        project.location = _clean(data.location, 255)

    if "description" in data.model_fields_set:
        project.description = _clean(data.description, 2000)

    if data.status is not None:
        project.status = _validate_status(data.status)

    for field in (
        "tender_start_date",
        "tender_submission_date",
        "expected_award_date",
        "planned_start_date",
        "planned_end_date",
        "actual_start_date",
        "actual_end_date",
    ):
        if field in data.model_fields_set:
            setattr(project, field, getattr(data, field))

    if data.award_probability is not None and not (
        0 <= data.award_probability <= 100
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Award probability must be between 0 and 100",
        )

    if "award_probability" in data.model_fields_set:
        project.award_probability = data.award_probability

    project.updated_by_id = current_user.id

    db.commit()
    db.refresh(project)

    return _to_detail(project)


@router.post("/{project_id}/archive", response_model=ProjectDetail)
def archive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.archive")),
) -> ProjectDetail:
    project = _require_visible_project(current_user, project_id, db)

    if project.archived_at is None:
        from datetime import UTC, datetime

        project.archived_at = datetime.now(UTC)
        project.updated_by_id = current_user.id
        db.commit()
        db.refresh(project)

    return _to_detail(project)


@router.post("/{project_id}/unarchive", response_model=ProjectDetail)
def unarchive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("projects.archive")),
) -> ProjectDetail:
    project = _require_visible_project(current_user, project_id, db)

    if project.archived_at is not None:
        project.archived_at = None
        project.updated_by_id = current_user.id
        db.commit()
        db.refresh(project)

    return _to_detail(project)


# --------------------------------------------------------------------------
# Project memberships (access scope)
# --------------------------------------------------------------------------


@router.get(
    "/{project_id}/memberships",
    response_model=list[ProjectMembershipResponse],
)
def list_project_memberships(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_memberships.view")
    ),
) -> list[ProjectMembershipResponse]:
    project = _require_visible_project(current_user, project_id, db)

    statement = (
        select(ProjectMembership)
        .where(ProjectMembership.project_id == project.id)
        .order_by(ProjectMembership.created_at)
    )

    return list(db.scalars(statement).all())


@router.post(
    "/{project_id}/memberships",
    response_model=ProjectMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_membership(
    project_id: int,
    data: ProjectMembershipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_memberships.manage")
    ),
) -> ProjectMembershipResponse:
    project = _project_by_id(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    user = db.get(User, data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown user",
        )

    existing = db.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == data.user_id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user already has access to this project",
        )

    membership = ProjectMembership(
        project_id=project_id,
        user_id=data.user_id,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        is_active=data.is_active,
        created_by_id=current_user.id,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


@router.patch(
    "/memberships/{membership_id}",
    response_model=ProjectMembershipResponse,
)
def update_project_membership(
    membership_id: int,
    data: ProjectMembershipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_memberships.manage")
    ),
) -> ProjectMembershipResponse:
    membership = db.get(ProjectMembership, membership_id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project membership not found",
        )

    if data.is_active is not None:
        membership.is_active = data.is_active

    if "valid_from" in data.model_fields_set:
        membership.valid_from = data.valid_from

    if "valid_to" in data.model_fields_set:
        membership.valid_to = data.valid_to

    db.commit()
    db.refresh(membership)

    return membership


@router.delete(
    "/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project_membership(
    membership_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_memberships.manage")
    ),
) -> None:
    membership = db.get(ProjectMembership, membership_id)

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project membership not found",
        )

    db.delete(membership)
    db.commit()


# --------------------------------------------------------------------------
# Project approvers
# --------------------------------------------------------------------------


VALID_APPROVAL_TYPES = {"assignment", "transfer", "leave"}


def _validate_approval_type(value: str) -> str:
    if value not in VALID_APPROVAL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown approval type {value!r}. "
                f"Valid: {', '.join(sorted(VALID_APPROVAL_TYPES))}"
            ),
        )

    return value


@router.get(
    "/{project_id}/approvers",
    response_model=list[ProjectApproverResponse],
)
def list_project_approvers(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project_approvers.view")),
) -> list[ProjectApproverResponse]:
    project = _require_visible_project(current_user, project_id, db)

    statement = (
        select(ProjectApprover)
        .where(ProjectApprover.project_id == project.id)
        .order_by(
            ProjectApprover.approval_type,
            ProjectApprover.sequence_order,
        )
    )

    return list(db.scalars(statement).all())


@router.post(
    "/{project_id}/approvers",
    response_model=ProjectApproverResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_approver(
    project_id: int,
    data: ProjectApproverCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_approvers.manage")
    ),
) -> ProjectApproverResponse:
    project = _project_by_id(db, project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    user = db.get(User, data.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unknown user",
        )

    approval_type = _validate_approval_type(data.approval_type)

    approver = ProjectApprover(
        project_id=project_id,
        user_id=data.user_id,
        approval_type=approval_type,
        sequence_order=data.sequence_order,
        is_required=data.is_required,
        valid_from=data.valid_from,
        valid_to=data.valid_to,
        is_active=data.is_active,
    )

    db.add(approver)
    db.commit()
    db.refresh(approver)

    return approver


@router.patch(
    "/approvers/{approver_id}",
    response_model=ProjectApproverResponse,
)
def update_project_approver(
    approver_id: int,
    data: ProjectApproverUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_approvers.manage")
    ),
) -> ProjectApproverResponse:
    approver = db.get(ProjectApprover, approver_id)

    if approver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project approver not found",
        )

    if data.approval_type is not None:
        approver.approval_type = _validate_approval_type(data.approval_type)

    if data.sequence_order is not None:
        approver.sequence_order = data.sequence_order

    if data.is_required is not None:
        approver.is_required = data.is_required

    if data.is_active is not None:
        approver.is_active = data.is_active

    if "valid_from" in data.model_fields_set:
        approver.valid_from = data.valid_from

    if "valid_to" in data.model_fields_set:
        approver.valid_to = data.valid_to

    db.commit()
    db.refresh(approver)

    return approver


@router.delete(
    "/approvers/{approver_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_project_approver(
    approver_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("project_approvers.manage")
    ),
) -> None:
    approver = db.get(ProjectApprover, approver_id)

    if approver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project approver not found",
        )

    db.delete(approver)
    db.commit()
