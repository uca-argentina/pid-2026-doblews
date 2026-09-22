"""What a person is allowed to do, and where.

The companion to auth.py: that one answers who you are and which firms you may
act in, this one answers what you may do once you are there. It is the only
module that reads role_permission, so moving a capability between roles stays a
row in the seed and never a change here.

Plain functions over the session, returning data and never raising
HTTPException. Turning an empty set into a 403 is the API layer's job, in
app/api/deps.py.

Implements step 3 of the request resolution in ADR-002 section 9.
"""

from typing import Literal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import FirmMember, Permission, PlatformMember, ProjectMember, RolePermission

# The three levels a role can be granted at, widest to narrowest. Same values as
# the CHECK constraint in models/role.py.
Scope = Literal["platform", "firm", "project"]

# The one permission code this application branches on outside a requires(...)
# declaration, so it is spelled once here rather than in each place that reads
# it. Firm-scope, held by the owner: it widens which *project* rows a read
# returns, and it is what decides whether a work the caller is not on is
# invisible to them or merely read-only (ADR-002 section 7).
VIEW_ALL = "project.view_all"


def _granted_codes(scope: Scope) -> Select:
    """Permission codes granted by a role, within one scope.

    The three functions below all start here and add the join that finds *whose*
    roles to look at. Keeping the catalogue half in one place means the rule
    "a permission code only means something inside a scope" (ADR-002 section 4)
    is written once.

    Joining on permission_id alone is enough: it is the primary key. And
    filtering role_permission.scope is enough to pin the permission's scope too,
    because the composite foreign key (permission_id, scope) -> permission
    (id, scope) already guarantees the two agree. Repeating the condition on
    permission would read as if it filtered something.
    """
    return (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.scope == scope)
    )


def platform_permissions(db: Session, account_id: int) -> frozenset[str]:
    """What this person may do to the platform itself. Empty for almost everyone.

    In production platform_member holds two or three rows forever, so this is
    empty for every real user and non-empty only for support.
    """
    return frozenset(
        db.scalars(
            _granted_codes("platform")
            .join(PlatformMember, PlatformMember.role_id == RolePermission.role_id)
            .where(PlatformMember.account_id == account_id)
        )
    )


def firm_permissions(db: Session, role_id: int) -> frozenset[str]:
    """What the holder of this firm role may do inside their firm.

    Takes the role_id rather than an account and a firm because the caller has
    already resolved the roster row: FirmMembership carries role_id precisely so
    this does not have to look the membership up a second time. That also means
    the roster and firm is_active checks already happened upstream, in
    get_firm_membership.
    """
    return frozenset(db.scalars(_granted_codes("firm").where(RolePermission.role_id == role_id)))


def project_permissions(
    db: Session, account_id: int, project_id: int, firm_id: int
) -> frozenset[str]:
    """What this person may do inside one project of one firm.

    The join against firm_member is the load-bearing part, not a formality.
    ADR-002 section 2: "la capa de estudio es la puerta de la capa de obra. Una
    fila en project_member no otorga nada si la fila de padrón de esa persona en
    ese estudio está inactiva." Since project_member has no is_active column of
    its own, that join is the only thing that makes those rows go inert when
    someone leaves the roster, which is what section 11.3 requires so their
    assignments come back untouched if they return.

    Passing firm_id gives isolation for free: a project belonging to another firm
    can never match, so this returns an empty set rather than leaking anything.

    Suspension of the whole firm is not checked here. Every project route hangs
    below /firms/{firm_id}, where get_current_membership has already refused a
    suspended firm with a 404.
    """
    return frozenset(
        db.scalars(
            _granted_codes("project")
            .join(ProjectMember, ProjectMember.role_id == RolePermission.role_id)
            .join(
                FirmMember,
                (FirmMember.firm_id == ProjectMember.firm_id)
                & (FirmMember.account_id == ProjectMember.account_id),
            )
            .where(
                ProjectMember.account_id == account_id,
                ProjectMember.project_id == project_id,
                ProjectMember.firm_id == firm_id,
                FirmMember.is_active,
            )
        )
    )
