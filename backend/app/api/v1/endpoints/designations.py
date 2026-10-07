from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.api.v1.endpoints._reference import (
    clean_code,
    clean_name,
    ensure_exists,
    ensure_unique_code,
)
from app.db.session import get_db
from app.models.reference import Department, Designation
from app.models.user import User
from app.schemas.reference import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
)

router = APIRouter(prefix="/designations", tags=["master-data"])


@router.get("/", response_model=list[DesignationResponse])
def list_designations(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_any_permission("master_data.view", "employees.view")
    ),
) -> list[DesignationResponse]:
    statement = select(Designation).order_by(Designation.sort_order, Designation.name)
    return list(db.scalars(statement).all())


@router.post(
    "/",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_designation(
    data: DesignationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> DesignationResponse:
    code = clean_code(data.code)
    name = clean_name(data.name)

    ensure_unique_code(db, Designation, code)

    if data.department_id is not None:
        ensure_exists(db, Department, data.department_id, "department")

    designation = Designation(
        code=code,
        name=name,
        department_id=data.department_id,
        description=data.description,
        sort_order=data.sort_order,
    )

    db.add(designation)
    db.commit()
    db.refresh(designation)

    return designation


@router.patch("/{designation_id}", response_model=DesignationResponse)
def update_designation(
    designation_id: int,
    data: DesignationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> DesignationResponse:
    designation = db.get(Designation, designation_id)

    if designation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found",
        )

    if data.code is not None:
        code = clean_code(data.code)

        if code != designation.code:
            ensure_unique_code(db, Designation, code, exclude_id=designation.id)
            designation.code = code

    if data.name is not None:
        designation.name = clean_name(data.name)

    if data.department_id is not None:
        ensure_exists(db, Department, data.department_id, "department")
        designation.department_id = data.department_id

    if "description" in data.model_fields_set:
        designation.description = data.description

    if data.sort_order is not None:
        designation.sort_order = data.sort_order

    if data.is_active is not None:
        designation.is_active = data.is_active

    db.commit()
    db.refresh(designation)

    return designation


@router.delete(
    "/{designation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_designation(
    designation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("master_data.manage")),
) -> None:
    designation = db.get(Designation, designation_id)

    if designation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found",
        )

    from app.models.employee import DesignationRate, Employee

    referenced = (
        db.scalar(
            select(Employee.id).where(Employee.designation_id == designation_id).limit(1)
        )
        is not None
        or db.scalar(
            select(DesignationRate.id)
            .where(DesignationRate.designation_id == designation_id)
            .limit(1)
        )
        is not None
    )

    if referenced:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This designation is referenced by employees or rates. "
                "Deactivate it instead of deleting."
            ),
        )

    db.delete(designation)
    db.commit()
