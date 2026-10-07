from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BusinessSetting(Base):
    """Configurable business configuration (spec #22).

    Deliberately a small key/value table: business rules such as the
    standard monthly hours (208) live in one place instead of being
    hard-coded independently in backend and frontend.
    """

    __tablename__ = "business_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        backref="updated_business_settings",
    )
