from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.api.v1.endpoints._reference import ensure_exists
from app.db.session import get_db
from app.models.employee import Employee
from app.models.reference import (
    Department,
    Designation,
    EmployeeCategory,
    ResourceProvider,
    Trade,
)
from app.models.user import User

router = APIRouter(prefix="/employees", tags=["employees"])

VALID_SOURCES = {"in_house", "hired"}
VALID_STATUSES = {"active", "inactive", "terminated"}


class EmployeeIn(BaseModel):
    employee_id: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    designation_id: int
    department_id: int | None = None
    employee_category_id: int | None = None
    trade_id: int | None = None
    employment_source: str = "in_house"
    resource_provider_id: int | None = None
    employment_status: str = "active"
    join_date: str | None = None
    termination_date: str | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class EmployeeOut(BaseModel):
    id: int
    employee_id: str
    full_name: str
    designation_id: int
    department_id: int | None
    employee_category_id: int | None
    trade_id: int | None
    employment_source: str
    resource_provider_id: int | None
    employment_status: str
    email: str | None
    phone: str | None
    notes: str | None

    model_config = ConfigDict(from_attributes=True)


class TerminateIn(BaseModel):
    termination_date: str


class EmployeeUpdate(BaseModel):
    """All-optional patch schema for employee edits."""

    employee_id: str | None = Field(default=None, min_length=1, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    designation_id: int | None = None
    department_id: int | None = None
    employee_category_id: int | None = None
    trade_id: int | None = None
    employment_source: str | None = None
    resource_provider_id: int | None = None
    employment_status: str | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


def _validate_source_rule(
    employment_source: str,
    resource_provider_id: int | None,
) -> None:
    if employment_source not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"employment_source must be one of: {', '.join(sorted(VALID_SOURCES))}"
            ),
        )

    if employment_source == "in_house" and resource_provider_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="In-house employees cannot reference a resource provider",
        )

    if employment_source == "hired" and resource_provider_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hired employees must reference a resource provider",
        )


def _validate_status(employment_status: str) -> None:
    if employment_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"employment_status must be one of: "
                f"{', '.join(sorted(VALID_STATUSES))}"
            ),
        )


def _validate_foreign_keys(db: Session, data: EmployeeIn) -> None:
    ensure_exists(db, Designation, data.designation_id, "designation")

    if data.department_id is not None:
        ensure_exists(db, Department, data.department_id, "department")

    if data.employee_category_id is not None:
        ensure_exists(
            db, EmployeeCategory, data.employee_category_id, "employee category"
        )

    if data.trade_id is not None:
        ensure_exists(db, Trade, data.trade_id, "trade")

    if data.resource_provider_id is not None:
        ensure_exists(
            db, ResourceProvider, data.resource_provider_id, "resource provider"
        )


@router.get("/", response_model=list[EmployeeOut])
def list_employees(
    designation_id: int | None = None,
    employment_source: str | None = None,
    employment_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission("employees.view", "planning.view")
    ),
) -> list[EmployeeOut]:
    statement = select(Employee).order_by(Employee.full_name)

    if designation_id is not None:
        statement = statement.where(Employee.designation_id == designation_id)

    if employment_source is not None:
        statement = statement.where(Employee.employment_source == employment_source)

    if employment_status is not None:
        statement = statement.where(Employee.employment_status == employment_status)

    return list(db.scalars(statement).all())


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission("employees.view", "planning.view")
    ),
) -> EmployeeOut:
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.post(
    "/",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    data: EmployeeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees.create")),
) -> EmployeeOut:
    employee_no = data.employee_id.strip()
    full_name = data.full_name.strip()

    if not employee_no or not full_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employee_id and full_name are required",
        )

    if db.scalar(select(Employee).where(Employee.employee_id == employee_no)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An employee with this ID already exists",
        )

    _validate_source_rule(data.employment_source, data.resource_provider_id)
    _validate_status(data.employment_status)
    _validate_foreign_keys(db, data)

    employee = Employee(
        employee_id=employee_no,
        full_name=full_name,
        first_name=data.first_name,
        middle_name=data.middle_name,
        last_name=data.last_name,
        designation_id=data.designation_id,
        department_id=data.department_id,
        employee_category_id=data.employee_category_id,
        trade_id=data.trade_id,
        employment_source=data.employment_source,
        resource_provider_id=data.resource_provider_id,
        employment_status=data.employment_status,
        email=data.email,
        phone=data.phone,
        notes=data.notes,
        created_by_id=current_user.id,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


@router.patch("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees.edit")),
) -> EmployeeOut:
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    updates = data.model_dump(exclude_unset=True)

    if "designation_id" in updates and updates["designation_id"] is not None:
        ensure_exists(db, Designation, updates["designation_id"], "designation")

    employee_no = updates.get("employee_id")

    if employee_no is not None and employee_no.strip() != employee.employee_id:
        clean = employee_no.strip()

        if not clean:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="employee_id is required",
            )

        if db.scalar(
            select(Employee).where(
                Employee.employee_id == clean, Employee.id != employee_id
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An employee with this ID already exists",
            )

        employee.employee_id = clean

    _validate_source_rule(
        updates.get("employment_source", employee.employment_source),
        updates.get("resource_provider_id", employee.resource_provider_id),
    )

    if "employment_status" in updates:
        _validate_status(updates["employment_status"])

    for field in (
        "full_name",
        "first_name",
        "middle_name",
        "last_name",
        "designation_id",
        "department_id",
        "employee_category_id",
        "trade_id",
        "email",
        "phone",
        "notes",
    ):
        if field in updates:
            setattr(employee, field, updates[field])

    employee.updated_by_id = current_user.id

    db.commit()
    db.refresh(employee)

    return employee


@router.post("/{employee_id}/terminate", response_model=EmployeeOut)
def terminate_employee(
    employee_id: int,
    data: TerminateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("employees.terminate")),
) -> EmployeeOut:
    """Termination keeps assignments intact (spec #85); status changes only."""
    employee = db.get(Employee, employee_id)

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    employee.employment_status = "terminated"
    employee.termination_date = datetime.fromisoformat(data.termination_date)
    employee.updated_by_id = current_user.id

    db.commit()
    db.refresh(employee)

    return employee
