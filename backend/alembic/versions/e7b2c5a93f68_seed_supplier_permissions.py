"""seed supplier permissions

Adds the two capabilities ADR-010 section 6 defines for HU-17 and HU-18: firm-scope
supplier.view and supplier.manage, both granted to owner and architect.

Two permissions here, unlike recipe.manage and project.budget.manage, because
reading is not a sub-case of writing: the per-material comparison of HU-18 asks
for supplier.view alone.

The client gets neither, and that is a decision and not an oversight: everything
in this section is the firm's costs. The per-work purchasing view needs no
permission of its own — it asks for what seeing the work's costs asks for,
project.cost.view or project.view_all.

Written out literally rather than imported from app/, for the same reason as the
migrations it follows: a migration is a frozen snapshot.

Revision ID: e7b2c5a93f68
Revises: d6a1f4b82e57
Create Date: 2026-10-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b2c5a93f68"
down_revision: str | Sequence[str] | None = "d6a1f4b82e57"
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
        "supplier.view",
        "firm",
        "Ver los proveedores del estudio, sus listas de precios y comparar alternativas de compra",
    ),
    (
        "supplier.manage",
        "firm",
        "Crear, editar y dar de baja los proveedores del estudio y los precios de su lista",
    ),
]

# The firm roles ADR-010 section 6 names. Not client: this is the firm's costs.
GRANTED_TO = ("owner", "architect")


def upgrade() -> None:
    """Add supplier.view and supplier.manage and grant them to owner and architect."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )

    # Ids are GENERATED ALWAYS, so they cannot be written: read back what the
    # database assigned and key it by (code, scope), which is the stable identity.
    permission_ids = bind.execute(
        sa.text(
            "SELECT id FROM permission"
            " WHERE scope = 'firm' AND code IN ('supplier.view', 'supplier.manage')"
        )
    ).scalars()
    role_ids = list(
        bind.execute(
            sa.text("SELECT id FROM role WHERE scope = 'firm' AND code IN :codes").bindparams(
                sa.bindparam("codes", expanding=True)
            ),
            {"codes": list(GRANTED_TO)},
        ).scalars()
    )

    op.bulk_insert(
        role_permission_table,
        [
            {"role_id": role_id, "permission_id": permission_id, "scope": "firm"}
            for permission_id in permission_ids
            for role_id in role_ids
        ],
    )


def downgrade() -> None:
    """Remove exactly the permissions this migration added.

    The role_permission rows go with them, since that table's foreign keys are
    ON DELETE CASCADE.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
