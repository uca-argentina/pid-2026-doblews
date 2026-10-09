"""The planning of one work: the tasks it is split into (HU-13, ADR-009).

A task stores what a person loads and what a change of status records. Its
planned dates, its slack and its cost are not here: they are computed on read,
because they depend on today's date and on the live take-off (ADR-009 section 2).
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# The four states the brief names. VARCHAR + CHECK, never a native ENUM
# (modelo-datos 3.7). Which one may follow which is a service rule (ADR-009
# section 5): a CHECK sees one row at a time and cannot see the previous value.
TASK_STATUS_CHECK = "status IN ('pending', 'in_progress', 'paused', 'finished')"


class ProjectTask(Base):
    """One task of a work: "Mampostería planta baja", 10 working days, pending.

    The four CHECKs on the actual dates say one thing between them: the dates a
    task carries are exactly the ones its status implies. A pending task has
    none, a started one has its start, and only a finished one has its end.
    """

    __tablename__ = "project_task"
    __table_args__ = (
        CheckConstraint("estimated_duration_days > 0", name="estimated_duration_days_positive"),
        CheckConstraint(TASK_STATUS_CHECK, name="status_valid"),
        CheckConstraint(
            "status <> 'pending' OR actual_start_date IS NULL",
            name="pending_has_no_actual_start",
        ),
        CheckConstraint(
            "status = 'pending' OR actual_start_date IS NOT NULL",
            name="started_has_actual_start",
        ),
        CheckConstraint(
            "(status = 'finished') = (actual_end_date IS NOT NULL)",
            name="actual_end_iff_finished",
        ),
        CheckConstraint(
            "actual_end_date >= actual_start_date",
            name="actual_end_not_before_start",
        ),
        # The composite FK of modelo-datos 3.8, as in project_recipe: a task of
        # another firm's work cannot be written, not merely refused.
        ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
        ),
        # Against firm_member and not project_member, which is really deleted
        # when someone leaves the team (ADR-009 section 6). What the schema
        # guarantees is that the assignee is on this firm's roster; that they may
        # manage this work's tasks is a service rule, checked when assigning.
        ForeignKeyConstraint(
            ["firm_id", "assignee_account_id"],
            ["firm_member.firm_id", "firm_member.account_id"],
        ),
        # Target of the composite FKs that must stay inside one work:
        # project_recipe.task_id today, the dependencies of HU-14 next.
        UniqueConstraint("id", "project_id"),
        Index("ix_project_task_project_id", "project_id"),
        # Every read filters by firm_id, from the base repository (ADR-002 8).
        Index("ix_project_task_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    project_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant on purpose: the column both composite FKs above share, which is
    # what ties the work and the assignee to the same firm.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)

    # Working days, Monday to Friday (ADR-009 section 4).
    estimated_duration_days: Mapped[int] = mapped_column(Integer)
    # "No antes de": the earliest day the task may be planned to start. A
    # calendar date, not an instant (modelo-datos 3.6).
    not_before_date: Mapped[date | None] = mapped_column(Date)

    status: Mapped[str] = mapped_column(String(20), server_default=text("'pending'"))

    assignee_account_id: Mapped[int | None] = mapped_column(BigInteger)

    # Recorded by starting and finishing the task, and correctable afterwards.
    actual_start_date: Mapped[date | None] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Unique on lower(name), per work, and only among the active tasks
# (modelo-datos 3.4): the name is a label, so a task removed by mistake can be
# loaded again under the same one.
Index(
    "uq_project_task_name_active",
    ProjectTask.project_id,
    func.lower(ProjectTask.name),
    unique=True,
    postgresql_where=text("is_active"),
)
