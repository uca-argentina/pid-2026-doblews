"""seed recipe manage permission

Adds the capability ADR-006 section 3 defines for HU-9: a firm-scope permission
to create, edit and deactivate the firm's own recipes, granted to owner and
architect. Reading them needs nothing new — catalog.view already covers the
combined listing of general and firm recipes, client included.

A single permission and not one per action, with the argument ADR-005 section 2
used for catalog.manage: no role fits part of it without the rest.

Written out literally rather than imported from app/, for the same reason as
the migrations it follows: a migration is a frozen snapshot.

Revision ID: c3e9a5d17f42
Revises: 8b4f2e6a1d37
Create Date: 2026-09-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e9a5d17f42"
down_revision: str | Sequence[str] | None = "8b4f2e6a1d37"
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
        "recipe.manage",
        "firm",
        "Crear, editar y dar de baja las recetas propias del estudio",
    ),
]

# The firm roles ADR-006 section 3 names. Not client: they read the recipes
# through catalog.view and never change them.
GRANTED_TO = ("owner", "architect")


def upgrade() -> None:
    """Add recipe.manage and grant it to owner and architect."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )

    # Ids are GENERATED ALWAYS, so they cannot be written: read back what the
    # database assigned and key it by (code, scope), which is the stable identity.
    permission_id = bind.execute(
        sa.text("SELECT id FROM permission WHERE code = 'recipe.manage' AND scope = 'firm'")
    ).scalar_one()
    role_ids = bind.execute(
        sa.text("SELECT id FROM role WHERE scope = 'firm' AND code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": list(GRANTED_TO)},
    ).scalars()

    op.bulk_insert(
        role_permission_table,
        [
            {"role_id": role_id, "permission_id": permission_id, "scope": "firm"}
            for role_id in role_ids
        ],
    )


def downgrade() -> None:
    """Remove exactly the permission this migration added.

    The role_permission rows go with it, since that table's foreign keys are
    ON DELETE CASCADE.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
