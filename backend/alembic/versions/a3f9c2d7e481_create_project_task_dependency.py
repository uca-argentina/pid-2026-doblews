"""create project task dependency

The other table of ADR-009 section 1, left out of d7c1e94a2b58 on purpose: it
belongs to HU-14, the story that reads and writes it.

A pure link, like recipe_resource: no is_active and no timestamps, so no
updated_at trigger either. No backfill: no work has dependencies yet.

Revision ID: a3f9c2d7e481
Revises: e2a6f0b3c719
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f9c2d7e481"
down_revision: str | Sequence[str] | None = "e2a6f0b3c719"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_task_dependency",
        sa.Column("predecessor_id", sa.BigInteger(), nullable=False),
        sa.Column("successor_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.CheckConstraint(
            "predecessor_id <> successor_id",
            name=op.f("ck_project_task_dependency_not_self"),
        ),
        # Both ends against project_task (id, project_id), sharing project_id:
        # the two tasks of a dependency are of the same work.
        sa.ForeignKeyConstraint(
            ["predecessor_id", "project_id"],
            ["project_task.id", "project_task.project_id"],
            name=op.f("fk_project_task_dependency_predecessor_id"),
        ),
        sa.ForeignKeyConstraint(
            ["successor_id", "project_id"],
            ["project_task.id", "project_task.project_id"],
            name=op.f("fk_project_task_dependency_successor_id"),
        ),
        sa.PrimaryKeyConstraint(
            "predecessor_id", "successor_id", name=op.f("pk_project_task_dependency")
        ),
    )
    op.create_index(
        "ix_project_task_dependency_successor_id",
        "project_task_dependency",
        ["successor_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_task_dependency_project_id",
        "project_task_dependency",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_project_task_dependency_project_id", table_name="project_task_dependency")
    op.drop_index("ix_project_task_dependency_successor_id", table_name="project_task_dependency")
    op.drop_table("project_task_dependency")
