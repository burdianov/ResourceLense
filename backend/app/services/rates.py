"""Rate history management and resolution.

Resolution precedence (spec #18/#21):
    1. Employee-specific rate effective on the target date
    2. Designation rate effective on the target date
    3. Missing-rate signal — never a silent zero
"""

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import DesignationRate, EmployeeRate
from app.services.settings import DEFAULT_MONTHLY_STANDARD_HOURS


@dataclass(frozen=True)
class ResolvedRate:
    hourly_rate: float
    currency_code: str
    source: str  # "employee" | "designation"
    source_record_id: int
    effective_from: datetime
    effective_to: datetime | None


def _effective_rate(
    records: list,
    target_date: datetime,
) -> tuple | None:
    """Return (record, index) of the rate effective on target_date, or None."""
    for record in records:
        starts_on_or_before = record.effective_from <= target_date

        if not starts_on_or_before:
            continue

        if record.effective_to is None or record.effective_to > target_date:
            return record

    return None


def assert_no_overlap(
    db: Session,
    model,
    owner_id: int,
    effective_from: datetime,
    effective_to: datetime | None,
    *,
    exclude_id: int | None = None,
    currency_code: str | None = None,
) -> None:
    """Reject overlapping effective periods for the same owner/currency.

    A new record may not overlap an existing open-ended record or any record
    whose [effective_from, effective_to) intersects the new period.
    """
    owner_column = (
        model.designation_id
        if model is DesignationRate
        else model.employee_id
    )

    statement = select(model).where(owner_column == owner_id)

    if currency_code is not None:
        statement = statement.where(model.currency_code == currency_code)

    if exclude_id is not None:
        statement = statement.where(model.id != exclude_id)

    for record in db.scalars(statement).all():
        existing_end = record.effective_to

        # Overlap test on half-open intervals [from, to).
        starts_inside = existing_end is None or effective_from < existing_end
        open_ended = effective_to is None
        ends_inside = (
            existing_end is not None
            and effective_to is not None
            and effective_to > record.effective_from
        )

        if starts_inside and (open_ended or ends_inside):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Rate period overlaps an existing rate effective from "
                    f"{record.effective_from.date()} to "
                    f"{existing_end.date() if existing_end else 'open'}"
                ),
            )


def resolve_rate(
    db: Session,
    *,
    employee_id: int | None,
    designation_id: int,
    target_date: datetime,
) -> ResolvedRate | None:
    """Resolve the applicable hourly rate for an employee on a date.

    Unnamed forecast lines pass ``employee_id=None`` and resolve straight
    to the designation rate. Returns None when no rate exists at all —
    callers must surface that as a validation error, never substitute zero.
    """
    employee_rate = None

    if employee_id is not None:
        employee_rate = _effective_rate(
            list(
                db.scalars(
                    select(EmployeeRate)
                    .where(EmployeeRate.employee_id == employee_id)
                    .order_by(EmployeeRate.effective_from.desc())
                ).all()
            ),
            target_date,
        )

    if employee_rate is not None:
        return ResolvedRate(
            hourly_rate=float(employee_rate.hourly_rate),
            currency_code=employee_rate.currency_code,
            source="employee",
            source_record_id=employee_rate.id,
            effective_from=employee_rate.effective_from,
            effective_to=employee_rate.effective_to,
        )

    designation_rate = _effective_rate(
        list(
            db.scalars(
                select(DesignationRate)
                .where(DesignationRate.designation_id == designation_id)
                .order_by(DesignationRate.effective_from.desc())
            ).all()
        ),
        target_date,
    )

    if designation_rate is not None:
        return ResolvedRate(
            hourly_rate=float(designation_rate.hourly_rate),
            currency_code=designation_rate.currency_code,
            source="designation",
            source_record_id=designation_rate.id,
            effective_from=designation_rate.effective_from,
            effective_to=designation_rate.effective_to,
        )

    return None


def require_rate(
    db: Session,
    *,
    employee_id: int | None,
    designation_id: int,
    target_date: datetime,
) -> ResolvedRate:
    """resolve_rate that raises a 422 instead of returning None."""
    resolved = resolve_rate(
        db,
        employee_id=employee_id,
        designation_id=designation_id,
        target_date=target_date,
    )

    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No hourly rate is effective for this employee or their "
                "designation on the target date"
            ),
        )

    return resolved


# Standard monthly hours (spec #22): one central definition.
MONTHLY_STANDARD_HOURS = DEFAULT_MONTHLY_STANDARD_HOURS


def monthly_cost(
    *,
    headcount: int = 1,
    allocation_percentage: float,
    hourly_rate: float,
    month_fraction: float = 1.0,
    standard_hours: float = float(DEFAULT_MONTHLY_STANDARD_HOURS),
) -> float:
    """Cost for one month: HC x pct x 208 x rate x month_fraction."""
    return (
        headcount
        * (allocation_percentage / 100.0)
        * standard_hours
        * hourly_rate
        * month_fraction
    )
