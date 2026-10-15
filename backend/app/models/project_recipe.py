"""The take-off of one work: which recipes it uses and how much of each.

The only table of ADR-003's five that holds a firm's data, so it is the only one
with firm_id and the only one with anything to isolate (ADR-003 section 7). It
references the catalogue and never copies it: the cost is read from the live
reference price at query time.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectRecipe(Base):
    """One line of a work's take-off: 120 m2 of "Pared de ladrillo comun 15cm".

    A row is a line of the take-off, not a physical object: eight walls of 15 m2
    are one row of 120 m2, because that is how a take-off is actually measured
    (ADR-003 section 5). There is deliberately no UNIQUE (project_id, recipe_id) —
    measuring the same recipe per storey is normal, and `note` is the label that
    tells those rows apart.
    """

    __tablename__ = "project_recipe"
    __table_args__ = (
        # Zero measured is not a line, it is a line someone forgot to fill in.
        CheckConstraint("quantity > 0", name="quantity_positive"),
        # The composite FK of modelo-datos 3.8, the same mechanism project_member
        # uses. Pointing this line at another firm's work is not rejected by a
        # service: it is impossible, because the pair has to exist in project.
        ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
        ),
        # A line belongs to at most one task, and only to a task of its own work
        # (ADR-009 section 1): the pair has to exist in project_task. With
        # task_id NULL the constraint is not checked, which is an unassigned line.
        ForeignKeyConstraint(
            ["task_id", "project_id"],
            ["project_task.id", "project_task.project_id"],
        ),
        # The take-off query of ADR-003 section 2 filters by project_id.
        Index("ix_project_recipe_project_id", "project_id"),
        # Every read filters by firm_id, from the base repository (ADR-002 8).
        Index("ix_project_recipe_firm_id", "firm_id"),
        # "The lines of this task", which is how a task's cost is added up.
        Index("ix_project_recipe_task_id", "task_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    project_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant on purpose: it is the column the composite FK above shares with
    # project, and carrying it is what ties this line to that work's firm.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    # Plain FK, not composite: the catalogue is global, so there is no firm to
    # match against.
    recipe_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recipe.id"))

    # The task this line is carried out in, or NULL while unassigned. Its cost
    # is what the task costs (ADR-009 section 8).
    task_id: Mapped[int | None] = mapped_column(BigInteger)

    # What was measured on site, in the recipe's own unit. Three decimals is
    # enough for a surface or a volume; this is not money either.
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    # Optional label that separates two lines of the same recipe: "planta baja".
    note: Mapped[str | None] = mapped_column(String(150))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
