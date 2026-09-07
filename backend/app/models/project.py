"""A construction project and the team working on it.

Project is the first business table, so it carries firm_id and every read filters
by it; project_member is where composite keys make cross-firm membership impossible.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    """One work. Belongs to exactly one firm and never moves between them."""

    __tablename__ = "project"
    __table_args__ = (
        # Target of project_member's composite FK: it is what proves a membership
        # row points at a project that really belongs to that firm.
        UniqueConstraint("id", "firm_id"),
        Index("ix_project_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # The tenant. Present in every query that reads this table (ADR-002 8).
    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("firm.id"))

    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(255))
    # A calendar date, not an instant: "it starts on October 15th" has no time
    # and no timezone (modelo-datos 3.6).
    estimated_start_date: Mapped[date | None] = mapped_column(Date)

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjectMember(Base):
    """The team of one project: one role per person per project.

    There is no project.client_id anywhere: the client of a project is its row
    here with the client role, and the partial index below guarantees there is
    at most one.
    """

    __tablename__ = "project_member"
    __table_args__ = (
        CheckConstraint("role_scope = 'project'", name="role_scope_fixed"),
        # The project really belongs to that firm...
        ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
        ),
        # ...and the person really is on that same firm's roster. Together these
        # two make putting someone from another firm into a project structurally
        # impossible, with no validation in Python.
        ForeignKeyConstraint(
            ["firm_id", "account_id"],
            ["firm_member.firm_id", "firm_member.account_id"],
        ),
        # Carries the role code too, so the partial indexes below have a literal
        # to test, and this FK is what keeps that code in sync with the role.
        ForeignKeyConstraint(
            ["role_id", "role_scope", "role_code"],
            ["role.id", "role.scope", "role.code"],
        ),
        # Two domain rules written straight into the schema (ADR-002 5).
        Index(
            "uq_project_member_lead",
            "project_id",
            unique=True,
            postgresql_where=text("role_code = 'lead'"),
        ),
        Index(
            "uq_project_member_client",
            "project_id",
            unique=True,
            postgresql_where=text("role_code = 'client'"),
        ),
        # "My projects", the first screen after login and the most frequent read
        # in the system.
        Index("ix_project_member_account_id", "account_id"),
    )

    project_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Redundant on purpose: it is the column the two composite FKs above share,
    # and sharing it is what ties the project and the person to the same firm.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    role_id: Mapped[int] = mapped_column(BigInteger)
    role_scope: Mapped[str] = mapped_column(String(20), server_default=text("'project'"))
    role_code: Mapped[str] = mapped_column(String(40))

    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
