"""Shared helpers for master reference-data endpoints.

All reference tables follow the same lifecycle: is_active instead of delete,
hard delete only when never referenced. This module centralizes the
list/create/update/deactivate pattern so each endpoint module stays thin.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def clean_code(value: str | None) -> str:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Code is required",
        )

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Code is required",
        )

    return cleaned


def clean_name(value: str | None) -> str:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name is required",
        )

    cleaned = value.strip()

    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name is required",
        )

    return cleaned


def get_by_code(db: Session, model, code: str):
    return db.scalar(select(model).where(model.code == code))


def ensure_unique_code(
    db: Session,
    model,
    code: str,
    *,
    exclude_id: int | None = None,
) -> None:
    statement = select(model).where(model.code == code)

    if exclude_id is not None:
        statement = statement.where(model.id != exclude_id)

    if db.scalar(statement) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A record with this code already exists",
        )


def ensure_exists(db: Session, model, record_id: int, label: str):
    record = db.get(model, record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown {label}: {record_id}",
        )

    return record
