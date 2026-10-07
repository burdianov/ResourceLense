from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import collect_permissions, require_permission
from app.api.scope import require_visible_project, visible_project_ids
from app.api.v1.endpoints._reference import ensure_exists
from app.db.session import get_db
from app.models.employee import Employee
from app.models.forecast import ForecastLine, ForecastVersion
from app.models.reference import Designation
from app.models.user import User
from app.schemas.forecast import (
    ForecastCloneRequest,
    ForecastLineCreate,
    ForecastLineUpdate,
    ForecastMonthsUpdate,
    ForecastVersionCreate,
    ForecastVersionDetail,
    ForecastVersionListItem,
    ForecastVersionUpdate,
)
from app.services import forecasts as forecast_service
from app.services.forecast_costs import build_version_detail

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


def _clean(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None


def _has_cost_permission(current_user: User) -> bool:
    """Rate and cost fields are hidden without forecasts.cost.view (spec #95)."""
    return "forecasts.cost.view" in collect_permissions(current_user)


def _get_version(db: Session, version_id: int) -> ForecastVersion:
    version = db.get(ForecastVersion, version_id)

    if version is None or version.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecast version not found",
        )

    return version


def _require_version_access(
    current_user: User,
    version: ForecastVersion,
    db: Session,
) -> None:
    require_visible_project(current_user, version.project_id, db)


def _get_line(db: Session, line_id: int) -> ForecastLine:
    line = db.get(ForecastLine, line_id)

    if line is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecast line not found",
        )

    return line


def _detail(
    db: Session,
    version: ForecastVersion,
    current_user: User,
) -> ForecastVersionDetail:
    return build_version_detail(
        db,
        version,
        include_cost=_has_cost_permission(current_user),
    )


def _validate_designation(db: Session, designation_id: int) -> Designation:
    designation = ensure_exists(db, Designation, designation_id, "designation")

    if not designation.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot forecast an inactive designation",
        )

    return designation


def _validate_employee(db: Session, employee_id: int) -> Employee:
    employee = ensure_exists(db, Employee, employee_id, "employee")

    if employee.employment_status == "terminated":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot plan a terminated employee",
        )

    return employee


# --- versions --------------------------------------------------------------


@router.get("/", response_model=list[ForecastVersionListItem])
def list_versions(
    project_id: int | None = None,
    forecast_type: str | None = None,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.view")),
) -> list[ForecastVersionListItem]:
    statement = (
        select(ForecastVersion)
        .where(ForecastVersion.deleted_at.is_(None))
        .order_by(
            ForecastVersion.project_id,
            ForecastVersion.forecast_type,
            ForecastVersion.version_no.desc(),
        )
    )

    if project_id is not None:
        statement = statement.where(ForecastVersion.project_id == project_id)

    if forecast_type is not None:
        statement = statement.where(
            ForecastVersion.forecast_type == forecast_type
        )

    if not include_archived:
        statement = statement.where(ForecastVersion.status != "archived")

    visible = visible_project_ids(current_user, db)

    if visible is not None:
        if not visible:
            return []

        statement = statement.where(ForecastVersion.project_id.in_(visible))

    return list(db.scalars(statement).all())


@router.post(
    "/",
    response_model=ForecastVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    data: ForecastVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.create")),
) -> ForecastVersionDetail:
    project = require_visible_project(current_user, data.project_id, db)

    if project.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot create a forecast for an archived project",
        )

    version = forecast_service.create_version(
        db,
        project_id=project.id,
        forecast_type=data.forecast_type,
        user=current_user,
        name=_clean(data.name),
        forecast_date=data.forecast_date,
        description=_clean(data.description),
    )

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.get("/{version_id}", response_model=ForecastVersionDetail)
def get_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.view")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    return _detail(db, version, current_user)


@router.patch("/{version_id}", response_model=ForecastVersionDetail)
def update_version(
    version_id: int,
    data: ForecastVersionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)
    forecast_service.ensure_draft(version)

    fields = data.model_fields_set

    if "name" in fields:
        version.name = _clean(data.name)

    if "forecast_date" in fields:
        version.forecast_date = data.forecast_date

    if "description" in fields:
        version.description = _clean(data.description)

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.post(
    "/{version_id}/clone",
    response_model=ForecastVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
def clone_version(
    version_id: int,
    data: ForecastCloneRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.create")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    clone = forecast_service.clone_version(
        db,
        version,
        current_user,
        name=_clean(data.name) if data is not None else None,
    )

    db.commit()
    db.refresh(clone)

    return _detail(db, clone, current_user)


@router.post("/{version_id}/publish", response_model=ForecastVersionDetail)
def publish_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.publish")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    forecast_service.publish_version(db, version, current_user)

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.post("/{version_id}/refresh-rates", response_model=ForecastVersionDetail)
def refresh_rates(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    forecast_service.refresh_rates(db, version)

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.post("/{version_id}/archive", response_model=ForecastVersionDetail)
def archive_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.publish")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    forecast_service.archive_version(db, version, current_user)

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    version_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> None:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)

    forecast_service.soft_delete_draft(db, version, current_user)

    db.commit()


# --- lines (draft editing) -------------------------------------------------


@router.post(
    "/{version_id}/lines",
    response_model=ForecastVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_line(
    version_id: int,
    data: ForecastLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> ForecastVersionDetail:
    version = _get_version(db, version_id)
    _require_version_access(current_user, version, db)
    forecast_service.ensure_draft(version)

    _validate_designation(db, data.designation_id)

    if data.employee_id is not None:
        _validate_employee(db, data.employee_id)

    line = ForecastLine(
        forecast_version_id=version.id,
        designation_id=data.designation_id,
        employee_id=data.employee_id,
        headcount=forecast_service.normalise_headcount(
            data.employee_id, data.headcount
        ),
        notes=_clean(data.notes),
        sort_order=data.sort_order,
    )

    db.add(line)
    db.flush()

    if data.months:
        forecast_service.set_month_cells(
            db,
            line,
            [
                (month.month, month.allocation_percentage)
                for month in data.months
            ],
        )

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.patch("/lines/{line_id}", response_model=ForecastVersionDetail)
def update_line(
    line_id: int,
    data: ForecastLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> ForecastVersionDetail:
    line = _get_line(db, line_id)
    version = line.version
    _require_version_access(current_user, version, db)
    forecast_service.ensure_draft(version)

    fields = data.model_fields_set
    identity_changed = False

    if "designation_id" in fields and data.designation_id is not None:
        if data.designation_id != line.designation_id:
            _validate_designation(db, data.designation_id)

            line.designation_id = data.designation_id
            identity_changed = True

    if "employee_id" in fields and data.employee_id != line.employee_id:
        if data.employee_id is not None:
            _validate_employee(db, data.employee_id)

        line.employee_id = data.employee_id
        identity_changed = True

    if "headcount" in fields and data.headcount is not None:
        line.headcount = data.headcount

    if "notes" in fields:
        line.notes = _clean(data.notes)

    if "sort_order" in fields and data.sort_order is not None:
        line.sort_order = data.sort_order

    # Named lines always represent exactly one person (spec #24).
    line.headcount = forecast_service.normalise_headcount(
        line.employee_id, line.headcount
    )

    if identity_changed:
        forecast_service.refresh_line_rates(db, line)

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.put("/lines/{line_id}/months", response_model=ForecastVersionDetail)
def set_line_months(
    line_id: int,
    data: ForecastMonthsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> ForecastVersionDetail:
    line = _get_line(db, line_id)
    version = line.version
    _require_version_access(current_user, version, db)
    forecast_service.ensure_draft(version)

    forecast_service.set_month_cells(
        db,
        line,
        [
            (month.month, month.allocation_percentage)
            for month in data.months
        ],
    )

    db.commit()
    db.refresh(version)

    return _detail(db, version, current_user)


@router.delete("/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line(
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("forecasts.edit")),
) -> None:
    line = _get_line(db, line_id)
    version = line.version
    _require_version_access(current_user, version, db)
    forecast_service.ensure_draft(version)

    # Forecast lines inside an unpublished draft are normal editing
    # operations and may be physically removed (spec #87).
    db.delete(line)
    db.commit()
