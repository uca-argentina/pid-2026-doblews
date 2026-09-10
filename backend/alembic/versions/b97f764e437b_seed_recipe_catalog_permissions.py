"""seed recipe catalog permissions

Adds the four capabilities ADR-003 section 8 defines for the recipe catalogue and
the material take-off: one of firm scope and three of project scope, plus the 13
rows wiring them to the roles that receive them.

This migration is the claim of ADR-002 being cashed in. That ADR argued a new
module should add capabilities as rows, not as conditionals, and ADR-003 repeated
it: "Ninguna de estas cuatro filas requiere tocar código de autorización: entran
en la migración de seed del catálogo." Nothing under app/ changes here.

Written out literally rather than imported from app/, for the same reason as the
migration it follows: a migration is a frozen snapshot, and importing live code
would make this one seed whatever the catalogue happens to be months from now.

Revision ID: b97f764e437b
Revises: eb71961b1f69
Create Date: 2026-09-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b97f764e437b"
down_revision: str | Sequence[str] | None = "eb71961b1f69"
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
    # firm: the catalogue belongs to the platform and is read-only, so viewing it
    # is the only capability it has. No role gets a write permission over it
    # because no endpoint writes to it (ADR-003).
    ("catalog.view", "firm", "Consultar el catálogo de materiales y recetas del sistema"),
    # project: the take-off of one work
    ("project.recipe.view", "project", "Ver el cómputo de la obra"),
    ("project.recipe.manage", "project", "Cargar, editar y dar de baja líneas del cómputo"),
    ("project.cost.view", "project", "Ver los costos estimados de la obra"),
]

# (role code, scope) -> the codes above that role receives, from the table in
# ADR-003 section 8.
ROLE_PERMISSIONS: dict[tuple[str, str], list[str]] = {
    # Every firm role reads the catalogue, the client included: it is the same
    # catalogue for everyone and it holds no firm's data.
    ("owner", "firm"): ["catalog.view"],
    ("architect", "firm"): ["catalog.view"],
    ("client", "firm"): ["catalog.view"],
    ("lead", "project"): [
        "project.recipe.view",
        "project.recipe.manage",
        "project.cost.view",
    ],
    ("collaborator", "project"): [
        "project.recipe.view",
        "project.recipe.manage",
        "project.cost.view",
    ],
    ("viewer", "project"): ["project.recipe.view", "project.cost.view"],
    # The one asymmetry that matters, and the reason viewer and client were
    # seeded as separate roles back in ADR-002 even though they granted the same
    # thing: the client sees how much material their work takes and never what it
    # costs the studio. "Un cliente no es 've menos': ve otra cosa."
    ("client", "project"): ["project.recipe.view"],
}


def upgrade() -> None:
    """Add the four permissions and wire them to their roles."""
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
                "role_id": role_ids[(role_code, scope)],
                "permission_id": permission_ids[(permission_code, scope)],
                "scope": scope,
            }
            for (role_code, scope), permission_codes in ROLE_PERMISSIONS.items()
            for permission_code in permission_codes
        ],
    )


def downgrade() -> None:
    """Remove exactly the four permissions this migration added.

    The role_permission rows go with them, since that table's foreign keys are
    ON DELETE CASCADE. The roles themselves are left alone: they belong to the
    migration before this one.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
