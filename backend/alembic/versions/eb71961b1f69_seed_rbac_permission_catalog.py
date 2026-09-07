"""seed rbac permission catalog

Loads the closed catalogue of ADR-002 section 7: 22 permissions, 8 roles and the
32 rows wiring them. Every database that ran `alembic upgrade head` has it, so no
deploy can end up with a schema that cannot authorize anybody.

The data is written out literally instead of imported from app/: a migration is a
frozen snapshot, and importing live code would make this September migration seed
whatever the catalogue happens to be in November.

Revision ID: eb71961b1f69
Revises: 4701f7919bbb
Create Date: 2026-09-07 15:23:10.690785

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eb71961b1f69"
down_revision: str | Sequence[str] | None = "4701f7919bbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Lightweight table definitions rather than the ORM models: a migration must keep
# working after the models change.
permission_table = sa.table(
    "permission",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("scope", sa.String),
    sa.column("description", sa.Text),
)

role_table = sa.table(
    "role",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("scope", sa.String),
    sa.column("name", sa.String),
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
    # platform: support administers accounts, never content
    ("firm.create", "platform", "Dar de alta un estudio en la plataforma"),
    ("firm.view", "platform", "Ver los datos de cualquier estudio"),
    ("firm.edit", "platform", "Editar los datos de cualquier estudio"),
    ("firm.suspend", "platform", "Suspender o reactivar un estudio"),
    ("account.create", "platform", "Crear una cuenta de usuario"),
    ("account.view", "platform", "Ver las cuentas de la plataforma"),
    ("account.edit", "platform", "Editar los datos de una cuenta"),
    ("account.deactivate", "platform", "Dar de baja una cuenta de la plataforma"),
    ("account.reset_password", "platform", "Resetear la contraseña de una cuenta"),
    # firm: acting inside one studio
    ("firm.view", "firm", "Ver los datos del estudio"),
    ("firm.edit", "firm", "Editar los datos del estudio"),
    ("member.view", "firm", "Ver el padrón del estudio"),
    ("member.add", "firm", "Agregar una persona al padrón del estudio"),
    ("member.edit_role", "firm", "Cambiar el rol de un miembro del estudio"),
    ("member.remove", "firm", "Dar de baja a un miembro del padrón"),
    ("project.create", "firm", "Crear una obra en el estudio"),
    ("project.view_all", "firm", "Ver todas las obras del estudio, no solo las propias"),
    # project: acting inside one work
    ("project.view", "project", "Ver la obra"),
    ("project.edit", "project", "Editar los datos de la obra"),
    ("project.archive", "project", "Dar de baja la obra"),
    ("project.member.view", "project", "Ver el equipo de la obra"),
    ("project.member.manage", "project", "Asignar y quitar miembros de la obra"),
]

# (code, scope, name, description). name is the label the UI renders.
ROLES: list[tuple[str, str, str, str]] = [
    (
        "support",
        "platform",
        "Soporte",
        "Staff del producto. Administra cuentas y estudios, nunca contenido.",
    ),
    (
        "owner",
        "firm",
        "Propietario",
        "Dueño del estudio. Gestiona el padrón y ve todas las obras.",
    ),
    (
        "architect",
        "firm",
        "Arquitecto",
        "Trabaja en las obras del estudio en las que participa.",
    ),
    (
        "client",
        "firm",
        "Cliente",
        "Pertenece al estudio para poder ver sus propias obras.",
    ),
    (
        "lead",
        "project",
        "Responsable",
        "Lidera la obra y gestiona su equipo.",
    ),
    (
        "collaborator",
        "project",
        "Colaborador",
        "Trabaja en la obra, sin gestionar el equipo.",
    ),
    (
        "viewer",
        "project",
        "Lector",
        "Ve la obra sin poder modificarla.",
    ),
    (
        "client",
        "project",
        "Cliente",
        "Ve su obra, sin los costos internos del estudio.",
    ),
]

# (role code, scope) -> permission codes, from the table in ADR-002 section 7.
# Sets are flat, not inherited: lead repeats what collaborator has, so that
# "what can a collaborator do?" is always a SELECT and never a computation.
ROLE_PERMISSIONS: dict[tuple[str, str], list[str]] = {
    ("support", "platform"): [
        "firm.create",
        "firm.view",
        "firm.edit",
        "firm.suspend",
        "account.create",
        "account.view",
        "account.edit",
        "account.deactivate",
        "account.reset_password",
    ],
    ("owner", "firm"): [
        "firm.view",
        "firm.edit",
        "member.view",
        "member.add",
        "member.edit_role",
        "member.remove",
        "project.create",
        "project.view_all",
    ],
    ("architect", "firm"): [
        "firm.view",
        "member.view",
        "project.create",
    ],
    ("client", "firm"): [
        "firm.view",
    ],
    ("lead", "project"): [
        "project.view",
        "project.edit",
        "project.archive",
        "project.member.view",
        "project.member.manage",
    ],
    ("collaborator", "project"): [
        "project.view",
        "project.edit",
        "project.member.view",
    ],
    ("viewer", "project"): [
        "project.view",
        "project.member.view",
    ],
    # Today the same as viewer. They exist apart because the difference shows up
    # with budgets: viewer will get budget.view_costs and client will not. A
    # client does not see less, it sees something else.
    ("client", "project"): [
        "project.view",
    ],
}


def upgrade() -> None:
    """Load the catalogue."""
    bind = op.get_bind()

    op.bulk_insert(
        permission_table,
        [{"code": code, "scope": scope, "description": desc} for code, scope, desc in PERMISSIONS],
    )
    op.bulk_insert(
        role_table,
        [
            {"code": code, "scope": scope, "name": name, "description": desc}
            for code, scope, name, desc in ROLES
        ],
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
    """Remove exactly the rows this migration added.

    By (code, scope) rather than TRUNCATE, so rows added by a later migration
    survive. The role_permission rows go with them: both its foreign keys are
    ON DELETE CASCADE.
    """
    bind = op.get_bind()

    for code, scope, *_ in ROLES:
        bind.execute(
            sa.text("DELETE FROM role WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
    for code, scope, *_ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permission WHERE code = :code AND scope = :scope"),
            {"code": code, "scope": scope},
        )
