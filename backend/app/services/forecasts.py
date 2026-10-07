"""Forecast version lifecycle: create, clone, publish, supersede (spec #23–#27).

Published forecasts are immutable. Revisions are made by cloning the
current version into a new draft. Rate snapshots are kept live on drafts
(refreshable) and frozen at publish time so historical pricing stays
reproducible even after rates change.
"""

from collections.abc import Iterable
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.forecast import (
    FORECAST_TYPES,
    ForecastLine,
    ForecastLineMonth,
    ForecastVersion,
)
from app.models.user import User
from app.services.rates import ResolvedRate, resolve_rate


def validate_forecast_type(forecast_type: str) -> str:
    if forecast_type not in FORECAST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unknown forecast type {forecast_type!r}. "
                f"Valid: {', '.join(FORECAST_TYPES)}"
            ),
        )

    return forecast_type


def month_start(value: date) -> date:
    """Months are always stored as the first day of the month (spec #25)."""
    return value.replace(day=1)


def month_target_datetime(month: date) -> datetime:
    """Resolution timestamp for a month cell: the start of that month."""
    return datetime.combine(month_start(month), time.min, tzinfo=timezone.utc)


def ensure_draft(version: ForecastVersion) -> None:
    """Only drafts may be edited; everything else is immutable (spec #28/#106)."""
    if version.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This forecast version has been deleted",
        )

    if version.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Forecast versions are immutable once published; this "
                f"version is {version.status!r}. Clone it into a new draft "
                "to revise it."
            ),
        )


def normalise_headcount(employee_id: int | None, headcount: int) -> int:
    """Named lines always represent exactly one person (spec #24)."""
    if employee_id is not None:
        return 1

    if headcount < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An unnamed forecast line must have a headcount of at least 1",
        )

    return headcount


def next_version_no(
    db: Session,
    project_id: int,
    forecast_type: str,
) -> int:
    highest = db.scalar(
        select(func.max(ForecastVersion.version_no)).where(
            ForecastVersion.project_id == project_id,
            ForecastVersion.forecast_type == forecast_type,
        )
    )

    return (highest or 0) + 1


def create_version(
    db: Session,
    *,
    project_id: int,
    forecast_type: str,
    user: User,
    name: str | None = None,
    forecast_date: date | None = None,
    description: str | None = None,
) -> ForecastVersion:
    validate_forecast_type(forecast_type)

    version = ForecastVersion(
        project_id=project_id,
        forecast_type=forecast_type,
        version_no=next_version_no(db, project_id, forecast_type),
        name=name,
        status="draft",
        forecast_date=forecast_date,
        description=description,
        is_current=False,
        created_by_id=user.id,
    )

    db.add(version)
    db.flush()

    return version


def resolve_cell_rate(
    db: Session,
    line: ForecastLine,
    month: date,
) -> ResolvedRate | None:
    """Employee rate first, designation rate second, else None (spec #21)."""
    return resolve_rate(
        db,
        employee_id=line.employee_id,
        designation_id=line.designation_id,
        target_date=month_target_datetime(month),
    )


def apply_cell_snapshot(
    db: Session,
    cell: ForecastLineMonth,
    line: ForecastLine,
) -> None:
    """(Re)resolve a cell's rate and store it as the cell's snapshot.

    On drafts this tracks the currently effective rate and can be
    re-applied through the Refresh Rates action; publish uses it to
    freeze rates. A missing rate clears the snapshot — never a zero.
    """
    resolved = resolve_cell_rate(db, line, cell.month)

    if resolved is None:
        cell.resolved_hourly_rate_snapshot = None
        cell.rate_source_snapshot = None
        cell.rate_source_id_snapshot = None
        cell.currency_code_snapshot = None

        return

    cell.resolved_hourly_rate_snapshot = resolved.hourly_rate
    cell.rate_source_snapshot = resolved.source
    cell.rate_source_id_snapshot = resolved.source_record_id
    cell.currency_code_snapshot = resolved.currency_code


def refresh_line_rates(db: Session, line: ForecastLine) -> None:
    for cell in line.months:
        apply_cell_snapshot(db, cell, line)


def refresh_rates(db: Session, version: ForecastVersion) -> None:
    """Refresh Rates action for a draft (spec #27)."""
    ensure_draft(version)

    for line in version.lines:
        refresh_line_rates(db, line)


def set_month_cells(
    db: Session,
    line: ForecastLine,
    cells: Iterable[tuple[date, float]],
) -> None:
    """Upsert monthly deployment cells on a (draft) line (spec #25)."""
    existing = {cell.month: cell for cell in line.months}

    for raw_month, allocation in cells:
        month = month_start(raw_month)
        cell = existing.get(month)

        if cell is None:
            cell = ForecastLineMonth(
                month=month,
                allocation_percentage=allocation,
            )
            line.months.append(cell)
            existing[month] = cell
        else:
            cell.allocation_percentage = allocation

        apply_cell_snapshot(db, cell, line)


def clone_version(
    db: Session,
    source: ForecastVersion,
    user: User,
    *,
    name: str | None = None,
) -> ForecastVersion:
    """Clone any readable version into a new draft (spec #23)."""
    if source.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot clone a deleted forecast version",
        )

    clone = ForecastVersion(
        project_id=source.project_id,
        forecast_type=source.forecast_type,
        version_no=next_version_no(
            db, source.project_id, source.forecast_type
        ),
        name=name if name is not None else source.name,
        status="draft",
        forecast_date=source.forecast_date,
        description=source.description,
        is_current=False,
        created_by_id=user.id,
    )

    db.add(clone)
    db.flush()

    for line in source.lines:
        new_line = ForecastLine(
            forecast_version_id=clone.id,
            designation_id=line.designation_id,
            employee_id=line.employee_id,
            headcount=line.headcount,
            notes=line.notes,
            sort_order=line.sort_order,
        )

        db.add(new_line)
        db.flush()

        for cell in line.months:
            new_cell = ForecastLineMonth(
                forecast_line_id=new_line.id,
                month=cell.month,
                allocation_percentage=cell.allocation_percentage,
            )
            db.add(new_cell)
            db.flush()

            # The draft resolves rates currently; publish will freeze them.
            apply_cell_snapshot(db, new_cell, new_line)

    return clone


def publish_version(
    db: Session,
    version: ForecastVersion,
    user: User,
) -> None:
    """Publish a draft, superseding the current version (spec #23/#27).

    Runs inside the endpoint's transaction: superseding the previous
    version, freezing rate snapshots and flipping status all succeed or
    all fail together.
    """
    ensure_draft(version)

    if not version.lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot publish a forecast with no lines",
        )

    previous_versions = db.scalars(
        select(ForecastVersion).where(
            ForecastVersion.project_id == version.project_id,
            ForecastVersion.forecast_type == version.forecast_type,
            ForecastVersion.is_current.is_(True),
            ForecastVersion.id != version.id,
        )
    ).all()

    now = datetime.now(timezone.utc)

    for previous in previous_versions:
        previous.is_current = False
        previous.status = "superseded"
        previous.superseded_at = now
        previous.superseded_by_id = user.id

    for line in version.lines:
        refresh_line_rates(db, line)

    version.status = "published"
    version.is_current = True
    version.published_at = now
    version.published_by_id = user.id


def archive_version(
    db: Session,
    version: ForecastVersion,
    user: User,
) -> None:
    """Archive a published/superseded forecast (spec #87).

    Published forecasts are never deleted; archiving hides them from the
    active lists while keeping the history intact.
    """
    if version.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This forecast version has been deleted",
        )

    if version.status == "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Draft forecasts are deleted rather than archived",
        )

    version.status = "archived"
    version.is_current = False

    if version.archived_at is None:
        version.archived_at = datetime.now(timezone.utc)


def soft_delete_draft(
    db: Session,
    version: ForecastVersion,
    user: User,
) -> None:
    """Draft-only soft delete so accidental deletions are recoverable (#87)."""
    ensure_draft(version)

    version.deleted_at = datetime.now(timezone.utc)
    version.deleted_by_id = user.id
