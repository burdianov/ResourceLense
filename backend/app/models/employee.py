from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    first_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    middle_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id", ondelete="restrict"), nullable=False
    )
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="set null"), nullable=True
    )
    employee_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee_categories.id", ondelete="set null"),
        nullable=True,
    )
    trade_id: Mapped[int | None] = mapped_column(
        ForeignKey("trades.id", ondelete="set null"), nullable=True
    )

    employment_source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="in_house"
    )
    resource_provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("resource_providers.id", ondelete="set null"),
        nullable=True,
    )

    employment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    join_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    termination_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    designation = relationship(
        "Designation",
        backref="employees",
    )
    department = relationship(
        "Department",
        backref="employees",
    )
    employee_category = relationship(
        "EmployeeCategory",
        backref="employees",
    )
    trade = relationship(
        "Trade",
        backref="employees",
    )
    resource_provider = relationship(
        "ResourceProvider",
        backref="employees",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_employees",
    )
    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        backref="updated_employees",
    )


class DesignationRate(Base):
    __tablename__ = "designation_rates"

    id: Mapped[int] = mapped_column(primary_key=True)

    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id", ondelete="CASCADE"), nullable=False
    )
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    designation = relationship(
        "Designation",
        backref="rates",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_designation_rates",
    )


class EmployeeRate(Base):
    __tablename__ = "employee_rates"

    id: Mapped[int] = mapped_column(primary_key=True)

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    hourly_rate: Mapped[float] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False
    )
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    employee = relationship(
        "Employee",
        backref="rates",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_employee_rates",
    )
