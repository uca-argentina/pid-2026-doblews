"""seed purchase order permissions

Adds the two capabilities ADR-011 section 6 defines for HU-20 to HU-22: firm-scope
purchase_order.view and purchase_order.manage, both granted to owner and architect.

Firm scope although an order belongs to a work: the team decided that the owner
and the firm's architects manage purchases whether or not they are on the work's
team, and a project permission would only reach those who are. The lead of every
work is covered, since a firm client cannot lead one.

The client gets neither: an order is the firm's costs, like a supplier's prices
(ADR-010 section 6). purchase_order.view is also what reads the firm's points
(ADR-012 section 6), so it needs no row of its own.

Written out literally rather than imported from app/, for the same reason as the
migrations it follows: a migration is a frozen snapshot.

Revision ID: b9d4f6a82c35
Revises: a8c3e5f71b24
Create Date: 2026-10-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b9d4f6a82c35"
down_revision: str | Sequence[str] | None = "a8c3e5f71b24"
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
        "purchase_order.view",
        "firm",
        "Ver las órdenes de compra del estudio y el nivel del estudio con sus proveedores",
    ),
    (
        "purchase_order.manage",
        "firm",
        "Generar, editar, emitir, anular y recibir las órdenes de compra del estudio",
    ),
]

# The firm roles ADR-011 section 6 names. Not client: this is the firm's costs.
GRANTED_TO = ("owner", "architect")


def upgrade() -> None:
    """Add purchase_order.view and .manage and grant them to owner and architect."""
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
            " WHERE scope = 'firm'"
            " AND code IN ('purchase_order.view', 'purchase_order.manage')"
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
