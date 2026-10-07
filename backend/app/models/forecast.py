from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

FORECAST_TYPES = ("tender", "job")
FORECAST_STATUSES = ("draft", "published", "superseded", "archived")

RATE_SOURCES = ("employee", "designation")


class ForecastVersion(Base):
    """A versioned forecast per project and forecast type (spec #23).

    Only one version of each type per project may be current; publishing
    supersedes the previous current version. Published versions are
    immutable — revise by cloning into a new draft.
    """

    __tablename__ = "forecast_versions"

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    forecast_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="draft"
    )
    forecast_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
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

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    published_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    superseded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    superseded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Draft soft delete only (spec #87); published versions are never deleted.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "forecast_type",
            "version_no",
            name="uq_forecast_versions_project_type_number",
        ),
        CheckConstraint(
            "forecast_type IN ('tender', 'job')",
            name="ck_forecast_versions_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'superseded', 'archived')",
            name="ck_forecast_versions_status",
        ),
        # At most one current version per project and forecast type.
        Index(
            "uq_forecast_versions_one_current",
            "project_id",
            "forecast_type",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index(
            "ix_forecast_versions_project_type",
            "project_id",
            "forecast_type",
        ),
    )

    project = relationship("Project", backref="forecast_versions")
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_forecast_versions",
    )
    published_by = relationship(
        "User",
        foreign_keys=[published_by_id],
        backref="published_forecast_versions",
    )
    superseded_by = relationship(
        "User",
        foreign_keys=[superseded_by_id],
        backref="superseded_forecast_versions",
    )

    lines: Mapped[list["ForecastLine"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="ForecastLine.sort_order, ForecastLine.id",
    )


class ForecastLine(Base):
    """One staffing requirement row of a forecast (spec #24).

    Duplicate designations are intentional and allowed. A named line
    (employee_id set) has headcount exactly 1; an unnamed line has
    headcount >= 1.
    """

    __tablename__ = "forecast_lines"

    id: Mapped[int] = mapped_column(primary_key=True)

    forecast_version_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id", ondelete="restrict"), nullable=False
    )
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="restrict"), nullable=True
    )

    headcount: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    notes: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
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

    __table_args__ = (
        CheckConstraint(
            "headcount >= 1", name="ck_forecast_lines_headcount_min"
        ),
        CheckConstraint(
            "employee_id IS NULL OR headcount = 1",
            name="ck_forecast_lines_named_headcount_one",
        ),
        Index("ix_forecast_lines_version", "forecast_version_id"),
        Index("ix_forecast_lines_designation", "designation_id"),
        Index("ix_forecast_lines_employee", "employee_id"),
    )

    version: Mapped[ForecastVersion] = relationship(back_populates="lines")
    designation = relationship(
        "Designation",
        backref="forecast_lines",
    )
    employee = relationship(
        "Employee",
        backref="forecast_lines",
    )
    months: Mapped[list["ForecastLineMonth"]] = relationship(
        back_populates="line",
        cascade="all, delete-orphan",
        order_by="ForecastLineMonth.month",
    )


class ForecastLineMonth(Base):
    """Monthly deployment cell of a forecast line (spec #25).

    The UI shows months as columns; the database stores them as rows.
    Monetary cost is never stored — only the frozen rate snapshot needed
    for historical reproducibility (spec #26/#27).
    """

    __tablename__ = "forecast_line_months"

    id: Mapped[int] = mapped_column(primary_key=True)

    forecast_line_id: Mapped[int] = mapped_column(
        ForeignKey("forecast_lines.id", ondelete="CASCADE"),
        nullable=False,
    )

    month: Mapped[date] = mapped_column(Date, nullable=False)
    allocation_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="0"
    )

    # Frozen at publish time so historical pricing stays reproducible.
    resolved_hourly_rate_snapshot: Mapped[float | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    rate_source_snapshot: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    rate_source_id_snapshot: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    currency_code_snapshot: Mapped[str | None] = mapped_column(
        String(3), nullable=True
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

    __table_args__ = (
        UniqueConstraint(
            "forecast_line_id",
            "month",
            name="uq_forecast_line_months_line_month",
        ),
        CheckConstraint(
            "allocation_percentage >= 0 AND allocation_percentage <= 100",
            name="ck_forecast_line_months_allocation_range",
        ),
        CheckConstraint(
            "EXTRACT(DAY FROM month) = 1",
            name="ck_forecast_line_months_month_first_day",
        ),
    )

    line: Mapped[ForecastLine] = relationship(back_populates="months")
