"""seed project task permissions

Adds the two capabilities ADR-009 section 9 defines for HU-13: reading a work's
planning and changing it. The same split, and the same roles, as
project.recipe.view / project.recipe.manage (ADR-003 section 8).

The client holds project.task.view on purpose: they see what is planned on their
work and who does it. What they do not see is what each task costs, and that is
not decided here — the routes ask for project.cost.view on top, which the client
has lacked since ADR-003.

One manage permission for every write (creating, editing, removing, changing the
status, assigning take-off lines), with the argument ADR-005 section 2 used for
catalog.manage: no role fits one of them without the others.

Written out literally rather than imported from app/, for the same reason as the
migrations it follows: a migration is a frozen snapshot.

Revision ID: e2a6f0b3c719
Revises: d7c1e94a2b58
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2a6f0b3c719"
down_revision: str | Sequence[str] | None = "d7c1e94a2b58"
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
    ("project.task.view", "project", "Ver la planificación de la obra"),
    (
        "project.task.manage",
        "project",
        "Cargar, editar y dar de baja tareas de la obra, y cambiar su estado",
    ),
]

# (role code, scope) -> the codes above that role receives, from the table in
# ADR-009 section 9.
ROLE_PERMISSIONS: dict[tuple[str, str], list[str]] = {
    ("lead", "project"): ["project.task.view", "project.task.manage"],
    ("collaborator", "project"): ["project.task.view", "project.task.manage"],
    ("viewer", "project"): ["project.task.view"],
    ("client", "project"): ["project.task.view"],
}


def upgrade() -> None:
    """Add the two permissions and wire them to their roles."""
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
    """Remove exactly the two permissions this migration added.

    The role_permission rows go with them, since that table's foreign keys are
    ON DELETE CASCADE.
    """
    bind = op.get_bind()

    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
