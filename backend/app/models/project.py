from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)

    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    client_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    location: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    description: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )

    # Lifecycle status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="tender"
    )

    # Tender dates
    tender_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tender_submission_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_award_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Planned dates
    planned_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Actual dates
    actual_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Tender planning
    award_probability: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )

    # Archival
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    archived_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=True
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

    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        backref="created_projects",
    )
    updated_by = relationship(
        "User",
        foreign_keys=[updated_by_id],
        backref="updated_projects",
    )
    archived_by = relationship(
        "User",
        foreign_keys=[archived_by_id],
        backref="archived_projects",
    )

    memberships: Mapped[list["ProjectMembership"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    approvers: Mapped[list["ProjectApprover"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class ProjectMembership(Base):
    __tablename__ = "project_memberships"

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="memberships")
    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="project_memberships",
    )


class ProjectApprover(Base):
    __tablename__ = "project_approvers"

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    approval_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    sequence_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    project = relationship("Project", back_populates="approvers")
    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="project_approver_assignments",
    )
