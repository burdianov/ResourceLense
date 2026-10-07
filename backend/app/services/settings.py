"""Configurable business settings (spec #22).

The 208-hour standard month must not be hard-coded independently in
multiple places; it is stored once in ``business_settings`` and read
through this module. The default is used when the row is missing (for
example in a fresh database before the seed migration runs).
"""

from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.settings import BusinessSetting

MONTHLY_STANDARD_HOURS_KEY = "monthly_standard_hours"
DEFAULT_MONTHLY_STANDARD_HOURS = Decimal("208")


def get_business_setting(db: Session, key: str) -> str | None:
    setting = db.get(BusinessSetting, key)

    return setting.value if setting is not None else None


def get_monthly_standard_hours(db: Session) -> Decimal:
    """Hours represented by a 100% allocation for one full month."""
    value = get_business_setting(db, MONTHLY_STANDARD_HOURS_KEY)

    if value is None:
        return DEFAULT_MONTHLY_STANDARD_HOURS

    try:
        hours = Decimal(value)
    except InvalidOperation:
        return DEFAULT_MONTHLY_STANDARD_HOURS

    if hours <= 0:
        return DEFAULT_MONTHLY_STANDARD_HOURS

    return hours
