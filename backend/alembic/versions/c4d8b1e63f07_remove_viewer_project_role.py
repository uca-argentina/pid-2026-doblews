"""remove viewer project role

Takes `viewer` out of the closed catalogue of ADR-002 section 7. It was the
role for someone who reads a work, costs included, without changing it — and
nobody could hold it who needed it. An outsider who should see costs enters the
firm as a client, and a firm client may only ever be a project client (section
11.2), so `viewer` was left to the firm's own architects, on works their owner
already sees whole through project.view_all.

Whoever holds it today becomes a collaborator. That is a decision and not a
default: the alternative was taking them off their works, and a viewer is by
construction an architect or the owner of the firm, so the write access this
hands them goes to someone the firm already trusts with works of their own. It
is also where an outgoing lead lands (HU-6).

A real DELETE, on a table that has no is_active: the catalogue of roles is not
business data with a history, it is the vocabulary the rest is written in. The
role's rows in role_permission go with it, through ON DELETE CASCADE.

Written out literally rather than imported from app/, for the same reason as the
migrations it follows: a migration is a frozen snapshot.

Revision ID: c4d8b1e63f07
Revises: a3f9c2d7e481
Create Date: 2026-10-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d8b1e63f07"
down_revision: str | Sequence[str] | None = "a3f9c2d7e481"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The role as eb71961b1f69 seeded it, and what it had been granted since
# (b97f764e437b, e2a6f0b3c719). Only the downgrade reads these.
VIEWER_NAME = "Lector"
VIEWER_DESCRIPTION = "Ve la obra sin poder modificarla."
VIEWER_PERMISSIONS = [
    "project.view",
    "project.member.view",
    "project.recipe.view",
    "project.cost.view",
    "project.task.view",
]

ROLE_ID = sa.text("SELECT id FROM role WHERE code = :code AND scope = 'project'")


def upgrade() -> None:
    """Move every viewer to collaborator, then drop the role."""
    bind = op.get_bind()

    collaborator_id = bind.execute(ROLE_ID, {"code": "collaborator"}).scalar_one()

    # role_code travels with role_id: the composite foreign key on project_member
    # checks the pair, so both are written in the same statement. No unique index
    # is in the way — those cover lead and client only — and nobody can end up
    # twice on a work, since the primary key is (project_id, account_id).
    bind.execute(
        sa.text(
            "UPDATE project_member"
            "   SET role_id = :collaborator_id, role_code = 'collaborator'"
            " WHERE role_scope = 'project' AND role_code = 'viewer'"
        ),
        {"collaborator_id": collaborator_id},
    )

    bind.execute(sa.text("DELETE FROM role WHERE code = 'viewer' AND scope = 'project'"))


def downgrade() -> None:
    """Put the role back, with the permissions it held.

    Not the assignments: which collaborators had been viewers is not recorded
    anywhere, so they stay collaborators. Nothing is lost by that — they keep
    every work they had — and the role is there again to be handed out.
    """
    bind = op.get_bind()

    bind.execute(
        sa.text(
            "INSERT INTO role (code, scope, name, description)"
            " VALUES ('viewer', 'project', :name, :description)"
        ),
        {"name": VIEWER_NAME, "description": VIEWER_DESCRIPTION},
    )
    viewer_id = bind.execute(ROLE_ID, {"code": "viewer"}).scalar_one()

    for code in VIEWER_PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO role_permission (role_id, permission_id, scope)"
                " SELECT :role_id, id, 'project' FROM permission"
                "  WHERE code = :code AND scope = 'project'"
            ),
            {"role_id": viewer_id, "code": code},
        )
