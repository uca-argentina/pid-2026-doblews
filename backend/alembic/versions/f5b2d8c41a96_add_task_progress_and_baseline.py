"""add task progress and baseline

The columns of ADR-009 section 13: how much of each task is done, and the
planned dates the progress is compared against once the planning is fixed.

The backfill runs before the CHECKs exist, and is what lets them be created:
every task is born at zero by the column's default, which is right for all of
them except the ones already finished, which are at a hundred by definition.

No baseline is backfilled. No work has fixed its planning yet, and inventing
one would compare today's progress against dates nobody agreed to.

Revision ID: f5b2d8c41a96
Revises: c4d8b1e63f07
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5b2d8c41a96"
down_revision: str | Sequence[str] | None = "c4d8b1e63f07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "project_task",
        sa.Column("progress_percent", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column("project_task", sa.Column("baseline_start_date", sa.Date(), nullable=True))
    op.add_column("project_task", sa.Column("baseline_end_date", sa.Date(), nullable=True))

    op.execute("UPDATE project_task SET progress_percent = 100 WHERE status = 'finished'")

    op.create_check_constraint(
        op.f("ck_project_task_progress_percent_range"),
        "project_task",
        "progress_percent BETWEEN 0 AND 100",
    )
    op.create_check_constraint(
        op.f("ck_project_task_pending_has_no_progress"),
        "project_task",
        "status <> 'pending' OR progress_percent = 0",
    )
    op.create_check_constraint(
        op.f("ck_project_task_finished_is_complete"),
        "project_task",
        "status <> 'finished' OR progress_percent = 100",
    )
    op.create_check_constraint(
        op.f("ck_project_task_baseline_dates_together"),
        "project_task",
        "(baseline_start_date IS NULL) = (baseline_end_date IS NULL)",
    )
    op.create_check_constraint(
        op.f("ck_project_task_baseline_end_not_before_start"),
        "project_task",
        "baseline_end_date >= baseline_start_date",
    )

    op.add_column("project", sa.Column("baseline_set_on", sa.Date(), nullable=True))
    op.add_column("project", sa.Column("baseline_end_date", sa.Date(), nullable=True))
    op.create_check_constraint(
        op.f("ck_project_baseline_dates_together"),
        "project",
        "(baseline_set_on IS NULL) = (baseline_end_date IS NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_project_baseline_dates_together"), "project", type_="check")
    op.drop_column("project", "baseline_end_date")
    op.drop_column("project", "baseline_set_on")

    for name in (
        "ck_project_task_baseline_end_not_before_start",
        "ck_project_task_baseline_dates_together",
        "ck_project_task_finished_is_complete",
        "ck_project_task_pending_has_no_progress",
        "ck_project_task_progress_percent_range",
    ):
        op.drop_constraint(op.f(name), "project_task", type_="check")
    op.drop_column("project_task", "baseline_end_date")
    op.drop_column("project_task", "baseline_start_date")
    op.drop_column("project_task", "progress_percent")
