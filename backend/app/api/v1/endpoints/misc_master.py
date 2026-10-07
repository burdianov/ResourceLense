from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_any_permission, require_permission
from app.api.v1.endpoints._reference import (
    clean_code,
    clean_name,
    ensure_unique_code,
)
from app.db.session import get_db
from app.models.employee import Employee
from app.models.reference import EmployeeCategory, ResourceProvider, Trade
from app.models.user import User
from app.schemas.reference import (
    EmployeeCategoryCreate,
    EmployeeCategoryResponse,
    EmployeeCategoryUpdate,
    ResourceProviderCreate,
    ResourceProviderResponse,
    ResourceProviderUpdate,
    TradeCreate,
    TradeResponse,
    TradeUpdate,
)

categories_router = APIRouter(prefix="/employee-categories", tags=["master-data"])
trades_router = APIRouter(prefix="/trades", tags=["master-data"])
providers_router = APIRouter(prefix="/resource-providers", tags=["master-data"])

_VIEW = require_any_permission("master_data.view", "employees.view")
_MANAGE = require_permission("master_data.manage")


def _get_or_404(db: Session, model, record_id: int, label: str):
    record = db.get(model, record_id)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} not found",
        )

    return record


# --------------------------------------------------------------------------
# Employee categories
# --------------------------------------------------------------------------


@categories_router.get("/", response_model=list[EmployeeCategoryResponse])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(_VIEW),
) -> list[EmployeeCategoryResponse]:
    statement = select(EmployeeCategory).order_by(EmployeeCategory.name)
    return list(db.scalars(statement).all())


@categories_router.post(
    "/",
    response_model=EmployeeCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    data: EmployeeCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> EmployeeCategoryResponse:
    code = clean_code(data.code)
    name = clean_name(data.name)

    ensure_unique_code(db, EmployeeCategory, code)

    category = EmployeeCategory(
        code=code,
        name=name,
        description=data.description,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


@categories_router.patch(
    "/{category_id}", response_model=EmployeeCategoryResponse
)
def update_category(
    category_id: int,
    data: EmployeeCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> EmployeeCategoryResponse:
    category = _get_or_404(db, EmployeeCategory, category_id, "Employee category")

    if data.code is not None:
        code = clean_code(data.code)

        if code != category.code:
            ensure_unique_code(
                db, EmployeeCategory, code, exclude_id=category.id
            )
            category.code = code

    if data.name is not None:
        category.name = clean_name(data.name)

    if "description" in data.model_fields_set:
        category.description = data.description

    if data.is_active is not None:
        category.is_active = data.is_active

    db.commit()
    db.refresh(category)

    return category


# --------------------------------------------------------------------------
# Trades
# --------------------------------------------------------------------------


@trades_router.get("/", response_model=list[TradeResponse])
def list_trades(
    db: Session = Depends(get_db),
    current_user: User = Depends(_VIEW),
) -> list[TradeResponse]:
    statement = select(Trade).order_by(Trade.name)
    return list(db.scalars(statement).all())


@trades_router.post(
    "/",
    response_model=TradeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_trade(
    data: TradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> TradeResponse:
    code = clean_code(data.code)
    name = clean_name(data.name)

    ensure_unique_code(db, Trade, code)

    trade = Trade(code=code, name=name, description=data.description)

    db.add(trade)
    db.commit()
    db.refresh(trade)

    return trade


@trades_router.patch("/{trade_id}", response_model=TradeResponse)
def update_trade(
    trade_id: int,
    data: TradeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> TradeResponse:
    trade = _get_or_404(db, Trade, trade_id, "Trade")

    if data.code is not None:
        code = clean_code(data.code)

        if code != trade.code:
            ensure_unique_code(db, Trade, code, exclude_id=trade.id)
            trade.code = code

    if data.name is not None:
        trade.name = clean_name(data.name)

    if "description" in data.model_fields_set:
        trade.description = data.description

    if data.is_active is not None:
        trade.is_active = data.is_active

    db.commit()
    db.refresh(trade)

    return trade


# --------------------------------------------------------------------------
# Resource providers
# --------------------------------------------------------------------------


@providers_router.get("/", response_model=list[ResourceProviderResponse])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(_VIEW),
) -> list[ResourceProviderResponse]:
    statement = select(ResourceProvider).order_by(ResourceProvider.name)
    return list(db.scalars(statement).all())


@providers_router.post(
    "/",
    response_model=ResourceProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_provider(
    data: ResourceProviderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> ResourceProviderResponse:
    code = clean_code(data.code)
    name = clean_name(data.name)

    ensure_unique_code(db, ResourceProvider, code)

    provider = ResourceProvider(
        code=code,
        name=name,
        legal_name=data.legal_name,
        contact_person=data.contact_person,
        email=data.email,
        phone=data.phone,
        notes=data.notes,
        created_by_id=current_user.id,
    )

    db.add(provider)
    db.commit()
    db.refresh(provider)

    return provider


@providers_router.patch(
    "/{provider_id}", response_model=ResourceProviderResponse
)
def update_provider(
    provider_id: int,
    data: ResourceProviderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> ResourceProviderResponse:
    provider = _get_or_404(db, ResourceProvider, provider_id, "Resource provider")

    if data.code is not None:
        code = clean_code(data.code)

        if code != provider.code:
            ensure_unique_code(
                db, ResourceProvider, code, exclude_id=provider.id
            )
            provider.code = code

    if data.name is not None:
        provider.name = clean_name(data.name)

    for field in (
        "legal_name",
        "contact_person",
        "email",
        "phone",
        "notes",
    ):
        if field in data.model_fields_set:
            setattr(provider, field, getattr(data, field))

    if data.is_active is not None:
        provider.is_active = data.is_active

    provider.updated_by_id = current_user.id

    db.commit()
    db.refresh(provider)

    return provider


@providers_router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_MANAGE),
) -> None:
    provider = _get_or_404(db, ResourceProvider, provider_id, "Resource provider")

    referenced = db.scalar(
        select(Employee.id)
        .where(Employee.resource_provider_id == provider_id)
        .limit(1)
    )

    if referenced is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This provider is referenced by employees. "
                "Deactivate it instead of deleting."
            ),
        )

    db.delete(provider)
    db.commit()
