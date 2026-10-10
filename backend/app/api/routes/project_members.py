"""The team of a work over HTTP (HU-6): who is on it, and who puts them there.

Every endpoint hangs below a work, so the 404 rules of ADR-002 section 9 are
already in force before any of this runs: an outsider never learns the work
exists, and someone who can see it but may not manage its team gets a 403 —
they already know it is there, so hiding it would protect nothing.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires,
)
from app.models import Project
from app.repositories.project import ProjectRepository
from app.repositories.project_team import ProjectTeamRepository, TeamEntry
from app.schemas.firm import RoleOut
from app.schemas.project_member import (
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectMemberRoleUpdate,
)
from app.services.project_team import (
    ProjectTeamError,
    TeamMemberNotFoundError,
    add_team_member,
    change_team_role,
    list_assignable_roles,
    remove_team_member,
)

router = APIRouter(
    prefix="/firms/{firm_id}/projects/{project_id}/members", tags=["project-members"]
)

TEAM_MEMBER_NOT_FOUND = "Esa persona no está en el equipo de esta obra"

# Declared once and reused by the four writes, so FastAPI resolves a single
# dependency object per request instead of four equivalent ones.
MANAGE = requires("project.member.manage", "project")


@contextmanager
def _team_rules() -> Iterator[None]:
    """Where a broken team rule becomes a status code, for every write here.

    409 and not 422, as in HU-2 and HU-3: the body was well formed, it is the
    state of the work or of the roster that refuses it — the candidate left the
    firm while the form was open, or the work already has a client. 422 stays
    for what Pydantic rejects.
    """
    try:
        yield
    except TeamMemberNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=TEAM_MEMBER_NOT_FOUND) from None
    except ProjectTeamError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _load_project(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> Project:
    """The work of the URL, or a 404.

    The guard already proved the caller holds something on this work, but not
    that the work is still live: project permissions resolve from project_member,
    which an archived work keeps. The base select of ProjectRepository filters
    is_active, so an archived work is a 404 here like on its own detail screen —
    and its team stays exactly as it was, which is what archiving promises.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account_id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _team(db: Session, membership: CurrentMembership, project_id: int) -> ProjectTeamRepository:
    """The repository, built with the firm the caller has already proved.

    From the resolved membership and never from the raw path, like every other
    repository in this package: {firm_id} is a string the caller chose, and
    get_current_membership is what turned it into a firm they belong to.
    """
    return ProjectTeamRepository(db, firm_id=membership.firm_id, project_id=project_id)


def _to_out(entry: TeamEntry) -> ProjectMemberOut:
    return ProjectMemberOut(
        account_id=entry.account_id,
        name=entry.name,
        email=entry.email,
        role=RoleOut(code=entry.role_code, name=entry.role_name),
        is_active=entry.is_active,
        joined_at=entry.joined_at,
    )


@router.get(
    "",
    response_model=list[ProjectMemberOut],
    dependencies=[Depends(requires("project.member.view", "project"))],
)
def list_team(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> list[ProjectMemberOut]:
    """Everyone on this work's team, the people who left the firm included.

    project.member.view and not manage, so a collaborator gets a 200 here: HU-6
    asks them to see the team and not to be able to change it. The
    firm's client does not hold it at all (ADR-002 section 7) and gets a 403 —
    who else works on the studio's side is not part of what a client is shown.

    The owner of the firm is in the same position, which is deliberate rather
    than an oversight: project.view_all lets them open any work of their firm,
    and it is not a project.member.* permission. The detail screen hands the
    frontend the project permissions it resolved, so the tab simply is not
    painted for them.
    """
    _load_project(db, membership, account.id, granted, project_id)
    return [_to_out(entry) for entry in _team(db, membership, project_id).list_team()]


@router.get("/roles", response_model=list[RoleOut], dependencies=[Depends(MANAGE)])
def list_roles(db: DbSession) -> list[RoleOut]:
    """The roles the add and edit forms offer, with their seeded Spanish labels.

    Behind manage, like HU-2's equivalent: the only screens that need them are
    the ones that assign, and those sit behind the same permission.
    """
    return [RoleOut(code=role.code, name=role.name) for role in list_assignable_roles(db)]


@router.post(
    "",
    response_model=ProjectMemberOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def add_member(
    project_id: int,
    payload: ProjectMemberAdd,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectMemberOut:
    """Put someone from the firm's roster on this work.

    Asking for lead transfers it in the same transaction: the person who holds it
    is left a collaborator and the new one takes the seat, so the work is never
    without a responsible and never with two.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _team_rules():
        add_team_member(db, project, account_id=payload.account_id, role_code=payload.role_code)
    db.commit()

    return _to_out(_team(db, membership, project_id).entry(payload.account_id))


@router.patch(
    "/{account_id}",
    response_model=ProjectMemberOut,
    dependencies=[Depends(MANAGE)],
)
def change_role(
    project_id: int,
    account_id: int,
    payload: ProjectMemberRoleUpdate,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectMemberOut:
    """Change someone's role on this work. The only field this edits.

    The caller comes in as the actor for the same reason as in HU-2: some of
    these rules are about who is asking, not only about who is named.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _team_rules():
        change_team_role(
            db,
            project,
            actor_id=account.id,
            account_id=account_id,
            role_code=payload.role_code,
        )
    db.commit()

    return _to_out(_team(db, membership, project_id).entry(account_id))


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def remove_member(
    project_id: int,
    account_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> None:
    """Take someone off this work's team.

    A real DELETE, unlike every other removal in the API: project_member has no
    is_active to flip, because an assignment is made inert by the roster row
    behind it and never by a flag (ADR-002 section 11.3).

    204 with no body: the frontend already has the row and only drops it.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _team_rules():
        remove_team_member(db, project, actor_id=account.id, account_id=account_id)
    db.commit()
