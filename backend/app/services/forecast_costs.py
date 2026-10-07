"""Dynamic FTE, hours and cost for forecast views (spec #26/#28/#29/#31).

Monetary values are never stored on forecast tables. They are derived
here from headcount, allocation and the rate snapshot:

- published versions use their frozen snapshot only, so historical
  pricing stays reproducible after rates change;
- drafts fall back to live rate resolution when a snapshot is missing;
- a missing rate is surfaced explicitly — never silently zero.

The monthly standard hours come from ``business_settings`` (spec #22).
"""

from sqlalchemy.orm import Session

from app.models.forecast import ForecastLine, ForecastLineMonth, ForecastVersion
from app.schemas.forecast import (
    ForecastLineResponse,
    ForecastLineSummary,
    ForecastMonthCell,
    ForecastVersionDetail,
)
from app.services.forecasts import month_target_datetime
from app.services.rates import resolve_rate
from app.services.settings import get_monthly_standard_hours


def build_version_detail(
    db: Session,
    version: ForecastVersion,
    *,
    include_cost: bool,
) -> ForecastVersionDetail:
    """Build the API representation, gating rate/cost fields (spec #95)."""
    hours_per_month = float(get_monthly_standard_hours(db))

    lines = [
        _build_line(db, version, line, hours_per_month, include_cost)
        for line in version.lines
    ]

    return ForecastVersionDetail(
        id=version.id,
        project_id=version.project_id,
        forecast_type=version.forecast_type,
        version_no=version.version_no,
        name=version.name,
        status=version.status,
        forecast_date=version.forecast_date,
        is_current=version.is_current,
        created_at=version.created_at,
        published_at=version.published_at,
        superseded_at=version.superseded_at,
        description=version.description,
        created_by_id=version.created_by_id,
        published_by_id=version.published_by_id,
        lines=lines,
    )


def _build_line(
    db: Session,
    version: ForecastVersion,
    line: ForecastLine,
    hours_per_month: float,
    include_cost: bool,
) -> ForecastLineResponse:
    cells = [
        _build_cell(db, version, line, cell, hours_per_month, include_cost)
        for cell in line.months
    ]

    active = [cell for cell in cells if cell.allocation_percentage > 0]
    total_hours = sum(cell.hours for cell in cells)
    average_fte = (
        sum(cell.fte for cell in active) / len(active) if active else 0.0
    )

    return ForecastLineResponse(
        id=line.id,
        designation_id=line.designation_id,
        designation_name=line.designation.name,
        employee_id=line.employee_id,
        employee_code=line.employee.employee_id if line.employee else None,
        employee_name=line.employee.full_name if line.employee else None,
        headcount=line.headcount,
        notes=line.notes,
        sort_order=line.sort_order,
        months=cells,
        summary=ForecastLineSummary(
            active_months=len(active),
            average_fte=round(average_fte, 4),
            total_hours=round(total_hours, 2),
        ),
    )


def _build_cell(
    db: Session,
    version: ForecastVersion,
    line: ForecastLine,
    cell: ForecastLineMonth,
    hours_per_month: float,
    include_cost: bool,
) -> ForecastMonthCell:
    allocation = float(cell.allocation_percentage)
    fte = line.headcount * allocation / 100.0
    hours = fte * hours_per_month

    payload = {
        "month": cell.month,
        "allocation_percentage": allocation,
        "fte": round(fte, 4),
        "hours": round(hours, 2),
    }

    if not include_cost:
        return ForecastMonthCell(**payload)

    rate = cell.resolved_hourly_rate_snapshot
    rate_source = cell.rate_source_snapshot
    currency = cell.currency_code_snapshot

    if rate is None and version.status == "draft":
        resolved = resolve_rate(
            db,
            employee_id=line.employee_id,
            designation_id=line.designation_id,
            target_date=month_target_datetime(cell.month),
        )

        if resolved is not None:
            rate = resolved.hourly_rate
            rate_source = resolved.source
            currency = resolved.currency_code

    if rate is None:
        return ForecastMonthCell(**payload, missing_rate=allocation > 0)

    return ForecastMonthCell(
        **payload,
        hourly_rate=float(rate),
        currency_code=currency,
        rate_source=rate_source,
        cost=round(hours * float(rate), 2),
        missing_rate=False,
    )
