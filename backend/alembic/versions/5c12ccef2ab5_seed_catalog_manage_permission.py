"""seed catalog manage permission

Adds the one capability ADR-005 section 2 defines for administering the system
catalogue at runtime: a platform-scope permission wired to support, and nothing
else. HU-8 is what uses it; the routes and the service come in later commits.

A single permission and not one per action (create/edit/deactivate), for the
reason ADR-005 gives: no role fits part of catalog.manage without the rest.

Written out literally rather than imported from app/, for the same reason as
the migrations it follows: a migration is a frozen snapshot, and importing
live code would make this one seed whatever the catalogue happens to be
months from now.

Revision ID: 5c12ccef2ab5
Revises: ce50de774991
Create Date: 2026-09-15 16:04:10.727565

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c12ccef2ab5"
down_revision: str | Sequence[str] | None = "ce50de774991"
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
        "catalog.manage",
        "platform",
        "Dar de alta, editar y dar de baja los materiales y recetas del catálogo",
    ),
]


def upgrade() -> None:
    """Add catalog.manage and grant it to support, the only role ADR-005 names."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )

    # Ids are GENERATED ALWAYS, so they cannot be written: read back what the
    # database assigned and key it by (code, scope), which is the stable identity.
    permission_id = bind.execute(
        sa.text("SELECT id FROM permission WHERE code = 'catalog.manage' AND scope = 'platform'")
    ).scalar_one()
    support_role_id = bind.execute(
        sa.text("SELECT id FROM role WHERE code = 'support' AND scope = 'platform'")
    ).scalar_one()

    op.bulk_insert(
        role_permission_table,
        [{"role_id": support_role_id, "permission_id": permission_id, "scope": "platform"}],
    )


def downgrade() -> None:
    """Remove exactly the permission this migration added.

    The role_permission row goes with it, since that table's foreign keys are
    ON DELETE CASCADE.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
