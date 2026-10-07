from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.api.v1.endpoints._reference import (
    clean_code,
    clean_name,
    ensure_exists,
    ensure_unique_code,
    get_by_code,
)
from app.db.session import get_db
from app.models.reference import Department, Designation
from app.models.user import User
from app.schemas.reference import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)

router = APIRouter(prefix="/departments", tags=["master-data"])


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission("master_data.view", "employees.view")
    ),
) -> list[DepartmentResponse]:
    statement = select(Department).order_by(Department.sort_order, Department.name)
    return list(db.scalars(statement).all())


@router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> DepartmentResponse:
    code = clean_code(data.code)
    name = clean_name(data.name)

    ensure_unique_code(db, Department, code)

    department = Department(
        code=code,
        name=name,
        description=data.description,
        sort_order=data.sort_order,
    )

    db.add(department)
    db.commit()
    db.refresh(department)

    return department


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> DepartmentResponse:
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    if data.code is not None:
        code = clean_code(data.code)

        if code != department.code:
            ensure_unique_code(db, Department, code, exclude_id=department.id)
            department.code = code

    if data.name is not None:
        department.name = clean_name(data.name)

    if "description" in data.model_fields_set:
        department.description = data.description

    if data.sort_order is not None:
        department.sort_order = data.sort_order

    if data.is_active is not None:
        department.is_active = data.is_active

    db.commit()
    db.refresh(department)

    return department


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> None:
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    referenced = db.scalar(
        select(Designation.id).where(Designation.department_id == department_id).limit(1)
    )

    if referenced is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This department is referenced by designations. "
                "Deactivate it instead of deleting."
            ),
        )

    db.delete(department)
    db.commit()
