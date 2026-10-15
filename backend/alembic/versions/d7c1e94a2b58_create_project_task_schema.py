"""create project task schema

The table HU-13 loads a work's tasks into, and the column that ties a take-off
line to one of them (ADR-009 section 1).

Two things here are deliberate rather than forgotten:

- project_task_dependency, the other table of that section, is not created
  here. It belongs to HU-14, which is the story that reads and writes it.
- project_recipe.task_id gets no backfill: every existing line stays NULL, which
  is exactly "unassigned", the state a line is in before anyone plans the work.

Revision ID: d7c1e94a2b58
Revises: b5e8a3f17c24
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7c1e94a2b58"
down_revision: str | Sequence[str] | None = "b5e8a3f17c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_task",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("firm_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("estimated_duration_days", sa.Integer(), nullable=False),
        sa.Column("not_before_date", sa.Date(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False
        ),
        sa.Column("assignee_account_id", sa.BigInteger(), nullable=True),
        sa.Column("actual_start_date", sa.Date(), nullable=True),
        sa.Column("actual_end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estimated_duration_days > 0",
            name=op.f("ck_project_task_estimated_duration_days_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'paused', 'finished')",
            name=op.f("ck_project_task_status_valid"),
        ),
        # The four below say one thing between them: a task carries exactly the
        # actual dates its status implies.
        sa.CheckConstraint(
            "status <> 'pending' OR actual_start_date IS NULL",
            name=op.f("ck_project_task_pending_has_no_actual_start"),
        ),
        sa.CheckConstraint(
            "status = 'pending' OR actual_start_date IS NOT NULL",
            name=op.f("ck_project_task_started_has_actual_start"),
        ),
        sa.CheckConstraint(
            "(status = 'finished') = (actual_end_date IS NOT NULL)",
            name=op.f("ck_project_task_actual_end_iff_finished"),
        ),
        sa.CheckConstraint(
            "actual_end_date >= actual_start_date",
            name=op.f("ck_project_task_actual_end_not_before_start"),
        ),
        # Composite, against project (id, firm_id): a task of another firm's
        # work cannot be written, not merely refused.
        sa.ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
            name=op.f("fk_project_task_project_id"),
        ),
        # Against firm_member and not project_member, which is really deleted
        # when someone leaves the team (ADR-009 section 6).
        sa.ForeignKeyConstraint(
            ["firm_id", "assignee_account_id"],
            ["firm_member.firm_id", "firm_member.account_id"],
            name=op.f("fk_project_task_firm_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_task")),
        # Target of project_recipe's composite FK below, and of HU-14's
        # dependencies: what keeps both inside one work.
        sa.UniqueConstraint("id", "project_id", name=op.f("uq_project_task_id_project_id")),
    )
    op.create_index("ix_project_task_firm_id", "project_task", ["firm_id"], unique=False)
    op.create_index("ix_project_task_project_id", "project_task", ["project_id"], unique=False)
    op.create_index(
        "uq_project_task_name_active",
        "project_task",
        ["project_id", sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.add_column("project_recipe", sa.Column("task_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_project_recipe_task_id"),
        "project_recipe",
        "project_task",
        ["task_id", "project_id"],
        ["id", "project_id"],
    )
    op.create_index("ix_project_recipe_task_id", "project_recipe", ["task_id"], unique=False)

    # Hand-written: autogenerate does not know about triggers. set_updated_at()
    # already exists — 4701f7919bbb created it — so only the trigger is new.
    op.execute("""
        CREATE TRIGGER trg_project_task_updated_at
        BEFORE UPDATE ON project_task
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    """Downgrade schema."""
    # The function itself is not dropped: it belongs to 4701f7919bbb.
    op.execute("DROP TRIGGER trg_project_task_updated_at ON project_task;")

    op.drop_index("ix_project_recipe_task_id", table_name="project_recipe")
    op.drop_constraint(op.f("fk_project_recipe_task_id"), "project_recipe", type_="foreignkey")
    op.drop_column("project_recipe", "task_id")

    op.drop_index(
        "uq_project_task_name_active",
        table_name="project_task",
        postgresql_where=sa.text("is_active"),
    )
    op.drop_index("ix_project_task_project_id", table_name="project_task")
    op.drop_index("ix_project_task_firm_id", table_name="project_task")
    op.drop_table("project_task")
