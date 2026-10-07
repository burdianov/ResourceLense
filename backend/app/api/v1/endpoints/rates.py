from datetime import datetime

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.v1.endpoints._reference import ensure_exists
from app.db.session import get_db
from app.models.employee import DesignationRate, EmployeeRate
from app.models.user import User
from app.services.rates import assert_no_overlap

router = APIRouter(prefix="/rates", tags=["rates"])


class DesignationRateCreate(BaseModel):
    designation_id: int
    hourly_rate: float = Field(ge=0)
    currency_code: str = Field(min_length=3, max_length=3)
    effective_from: datetime
    effective_to: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class DesignationRateResponse(BaseModel):
    id: int
    designation_id: int
    hourly_rate: float
    currency_code: str
    effective_from: datetime
    effective_to: datetime | None
    notes: str | None
    created_by_id: int

    model_config = ConfigDict(from_attributes=True)


class EmployeeRateCreate(BaseModel):
    employee_id: int
    hourly_rate: float = Field(ge=0)
    currency_code: str = Field(min_length=3, max_length=3)
    effective_from: datetime
    effective_to: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class EmployeeRateResponse(BaseModel):
    id: int
    employee_id: int
    hourly_rate: float
    currency_code: str
    effective_from: datetime
    effective_to: datetime | None
    notes: str | None
    created_by_id: int

    model_config = ConfigDict(from_attributes=True)


@router.get("/designations", response_model=list[DesignationRateResponse])
def list_designation_rates(
    designation_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.view")),
) -> list[DesignationRateResponse]:
    statement = select(DesignationRate).order_by(
        DesignationRate.designation_id, DesignationRate.effective_from
    )

    if designation_id is not None:
        statement = statement.where(DesignationRate.designation_id == designation_id)

    return list(db.scalars(statement).all())


@router.post(
    "/designations",
    response_model=DesignationRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_designation_rate(
    data: DesignationRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.manage")),
) -> DesignationRateResponse:
    from app.models.reference import Designation

    ensure_exists(db, Designation, data.designation_id, "designation")

    if data.effective_to is not None and data.effective_to <= data.effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after effective_from",
        )

    assert_no_overlap(
        db,
        DesignationRate,
        data.designation_id,
        data.effective_from,
        data.effective_to,
        currency_code=data.currency_code,
    )

    rate = DesignationRate(
        designation_id=data.designation_id,
        hourly_rate=data.hourly_rate,
        currency_code=data.currency_code.upper(),
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        notes=data.notes,
        created_by_id=current_user.id,
    )

    db.add(rate)
    db.commit()
    db.refresh(rate)

    return rate


@router.get("/employees", response_model=list[EmployeeRateResponse])
def list_employee_rates(
    employee_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.view")),
) -> list[EmployeeRateResponse]:
    statement = select(EmployeeRate).order_by(
        EmployeeRate.employee_id, EmployeeRate.effective_from
    )

    if employee_id is not None:
        statement = statement.where(EmployeeRate.employee_id == employee_id)

    return list(db.scalars(statement).all())


@router.post(
    "/employees",
    response_model=EmployeeRateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_employee_rate(
    data: EmployeeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.manage")),
) -> EmployeeRateResponse:
    from app.models.employee import Employee

    ensure_exists(db, Employee, data.employee_id, "employee")

    if data.effective_to is not None and data.effective_to <= data.effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after effective_from",
        )

    assert_no_overlap(
        db,
        EmployeeRate,
        data.employee_id,
        data.effective_from,
        data.effective_to,
        currency_code=data.currency_code,
    )

    rate = EmployeeRate(
        employee_id=data.employee_id,
        hourly_rate=data.hourly_rate,
        currency_code=data.currency_code.upper(),
        effective_from=data.effective_from,
        effective_to=data.effective_to,
        notes=data.notes,
        created_by_id=current_user.id,
    )

    db.add(rate)
    db.commit()
    db.refresh(rate)

    return rate


@router.post(
    "/employees/{rate_id}/end",
    response_model=EmployeeRateResponse,
)
def end_employee_rate(
    rate_id: int,
    effective_to: datetime,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.manage")),
) -> EmployeeRateResponse:
    """Close a rate period instead of deleting it (spec #88)."""
    rate = db.get(EmployeeRate, rate_id)

    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found",
        )

    if effective_to <= rate.effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after the rate start",
        )

    assert_no_overlap(
        db,
        EmployeeRate,
        rate.employee_id,
        rate.effective_from,
        effective_to,
        exclude_id=rate.id,
        currency_code=rate.currency_code,
    )

    rate.effective_to = effective_to
    db.commit()
    db.refresh(rate)

    return rate


@router.post(
    "/designations/{rate_id}/end",
    response_model=DesignationRateResponse,
)
def end_designation_rate(
    rate_id: int,
    effective_to: datetime,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("rates.manage")),
) -> DesignationRateResponse:
    rate = db.get(DesignationRate, rate_id)

    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate not found",
        )

    if effective_to <= rate.effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be after the rate start",
        )

    assert_no_overlap(
        db,
        DesignationRate,
        rate.designation_id,
        rate.effective_from,
        effective_to,
        exclude_id=rate.id,
        currency_code=rate.currency_code,
    )

    rate.effective_to = effective_to
    db.commit()
    db.refresh(rate)

    return rate
