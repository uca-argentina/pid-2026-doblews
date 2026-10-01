"""seed budget manage permission

Adds the capability ADR-007 section 4 defines for HU-12: a project-scope
permission to save a budget version and to load one back into the draft, granted
to lead and collaborator.

One permission for both actions, with the argument ADR-005 section 2 used for
catalog.manage and ADR-006 section 3 for recipe.manage: no role fits one without
the other.

Reading versions adds nothing. HU-12 asks for "lo mismo que ver el costo", so
the routes reuse project.cost.view or project.view_all — which is also why the
client, who holds neither, does not see them. That is a decision and not an
oversight: it is easy to assume every new capability brings its own permission,
and here it actively does not.

Written out literally rather than imported from app/, for the same reason as the
migrations it follows: a migration is a frozen snapshot.

Revision ID: b5e8a3f17c24
Revises: a4f7d2c8b901
Create Date: 2026-10-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5e8a3f17c24"
down_revision: str | Sequence[str] | None = "a4f7d2c8b901"
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
        "project.budget.manage",
        "project",
        "Guardar versiones del presupuesto de la obra y cargar una anterior",
    ),
]

# The project roles ADR-007 section 4 names. Not viewer and not client: they read
# the budget through project.cost.view and never freeze or replace it.
GRANTED_TO = ("lead", "collaborator")


def upgrade() -> None:
    """Add project.budget.manage and grant it to lead and collaborator."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )

    # Ids are GENERATED ALWAYS, so they cannot be written: read back what the
    # database assigned and key it by (code, scope), which is the stable identity.
    permission_id = bind.execute(
        sa.text(
            "SELECT id FROM permission"
            " WHERE code = 'project.budget.manage' AND scope = 'project'"
        )
    ).scalar_one()
    role_ids = bind.execute(
        sa.text("SELECT id FROM role WHERE scope = 'project' AND code IN :codes").bindparams(
            sa.bindparam("codes", expanding=True)
        ),
        {"codes": list(GRANTED_TO)},
    ).scalars()

    op.bulk_insert(
        role_permission_table,
        [
            {"role_id": role_id, "permission_id": permission_id, "scope": "project"}
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
