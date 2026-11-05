"""seed budget version view permission

The one row HU-25 needs: a project-scope permission that opens the saved budget
versions, and nothing else (ADR-013 section 1).

Why a permission of its own instead of giving the client project.cost.view:
that one would also open the live budget on the take-off, the cost of every
task, the dashboard and the purchasing comparison, which stay internal. A saved
version is the opposite of internal — it is the budget the studio froze in order
to present it to someone — so it gets a door of its own, narrow enough to hand
the client the key.

lead and collaborator receive it too, so nobody loses what they see today: the
read guard they used to pass with project.cost.view now asks for this one. The
owner keeps entering through project.view_all, as everywhere else.

Written out literally rather than imported from app/, like every other seed
migration here: a migration is a frozen snapshot.

Revision ID: e5a3c82f41d7
Revises: d4b7e1c93a56
Create Date: 2026-11-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a3c82f41d7"
down_revision: str | Sequence[str] | None = "d4b7e1c93a56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


permission_table = sa.table(
    "permission",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("scope", sa.String),
    sa.column("description", sa.Text),
)

role_permission_table = sa.table(
    "role_permission",
    sa.column("role_id", sa.BigInteger),
    sa.column("permission_id", sa.BigInteger),
    sa.column("scope", sa.String),
)

# (code, scope, description). Descriptions are UI text, so they stay in Spanish.
PERMISSIONS: list[tuple[str, str, str]] = [
    (
        "project.budget_version.view",
        "project",
        "Ver los presupuestos guardados de la obra",
    ),
]

# The project roles of ADR-013 section 1. The client is the point of the story;
# the other two are here so the read they already had does not close on them.
GRANTED_TO = ("lead", "collaborator", "client")
SCOPE = "project"


def upgrade() -> None:
    """Add project.budget_version.view and grant it to lead, collaborator and client."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )

    # Ids are GENERATED ALWAYS, so they cannot be written: read back what the
    # database assigned and key it by (code, scope), which is the stable identity.
    permission_ids = {
        (row.code, row.scope): row.id
        for row in bind.execute(sa.text("SELECT id, code, scope FROM permission"))
    }
    role_ids = {
        (row.code, row.scope): row.id
        for row in bind.execute(sa.text("SELECT id, code, scope FROM role"))
    }

    op.bulk_insert(
        role_permission_table,
        [
            {
                "role_id": role_ids[(role_code, SCOPE)],
                "permission_id": permission_ids[(code, SCOPE)],
                "scope": SCOPE,
            }
            for role_code in GRANTED_TO
            for code, scope, *_ in PERMISSIONS
        ],
    )


def downgrade() -> None:
    """Remove exactly the permission this migration added.

    The role_permission rows go with it, since that table's foreign keys are
    ON DELETE CASCADE. The roles themselves belong to earlier migrations.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
