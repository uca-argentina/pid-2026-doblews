"""The rules for changing who is on a work's team (HU-6).

Plain functions over the session, like the rest of the services: they return
data and never raise HTTPException. A broken rule is a ProjectTeamError, and
turning it into a status code is the API layer's job.

They flush and never commit. The route owns the transaction, which is what lets
a lead transfer — demote the one there, promote the new one — be a single
atomic act. HU-6: "el anterior queda como collaborator, la obra nunca se queda
sin responsable ni con dos".

services/project.py writes project_member too, as a side effect of creating or
editing a work. This module is the screen that manages those same rows head-on,
so it borrows that module's three helpers rather than keeping a second idea of
how a role code becomes a row.
"""

from typing import Literal, get_args

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Role
from app.repositories.project_team import ProjectTeamRepository
from app.services.project import (
    CLIENT,
    FIRM_CLIENT,
    LEAD,
    assign_role,
    firm_role_code,
    project_role,
)

# The project roles a lead may hand out, which is the whole catalogue (ADR-002
# section 7). Unlike the firm roster, where owner is deliberately withheld, there
# is nothing to withhold here: the work's own responsible is one of these, and
# handing it over is what a transfer is.
#
# A Literal rather than a list so the request schemas can use it as a field type:
# a role that is not one of these — a firm-scope code like "architect", say — is
# then a 422 from Pydantic before any code in this module runs.
AssignableProjectRole = Literal["lead", "collaborator", "viewer", "client"]

# Where the outgoing lead lands on a transfer. Not viewer: the person who was
# running the work keeps being able to work on it, they only stop answering for
# it. HU-6 names this role specifically.
DEMOTED_LEAD = "collaborator"

# What the lead reads when a rule says no. Spanish, because they are rendered as
# they are, and constants so the tests assert against these very strings.
NOT_ON_ROSTER = (
    "Esa persona no es miembro activo del estudio. "
    "Sumala al padrón antes de asignarla a la obra."
)
ALREADY_ON_TEAM = "Esa persona ya está en el equipo de esta obra"
FIRM_CLIENT_ONLY_AS_CLIENT = (
    "Un cliente del estudio solo puede participar de una obra como cliente. "
    "Asignale el rol de cliente, o cambiale el rol en el padrón del estudio."
)
ALREADY_HAS_CLIENT = "Esta obra ya tiene un cliente. Quitá al actual antes de asignar otro."
LEAD_IS_TRANSFERRED = (
    "La obra no puede quedarse sin responsable. Asignale el rol a otra persona: "
    "se transfiere solo, y quien lo tiene ahora queda como colaborador."
)
CANNOT_LEAVE_AS_LEAD = (
    "Sos el responsable de esta obra. Transferí el rol a otra persona antes de salir."
)


class ProjectTeamError(Exception):
    """A team rule refused the change. Nothing was written.

    Carries the message the lead reads, so the route passes it through without
    keeping a second table of texts.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class TeamMemberNotFoundError(Exception):
    """Nobody with that account is on this work's team.

    One error for "never assigned", "on another work" and "no such account",
    because the API answers all of them with the same 404 and must not hint at
    which one it was.
    """


def list_assignable_roles(db: Session) -> list[Role]:
    """The project roles the add and edit forms offer, with their seeded labels.

    Read from the role table rather than written out here, so the labels are the
    ones the seed holds and the frontend keeps no dictionary of its own. No firm
    filter: the catalogue is the same for every firm (ADR-002 section 4).

    Every role is offered to every candidate; it is the *candidate* that narrows
    the list, not the work. HU-6 asks the picker not to offer the other three to
    a firm client, and the frontend can tell because the roster it feeds from
    carries each person's firm role. The same rule is enforced here regardless,
    in _check_candidate, for requests that do not come from that form.
    """
    return list(
        db.scalars(
            select(Role)
            .where(Role.scope == "project", Role.code.in_(get_args(AssignableProjectRole)))
            .order_by(Role.code)
        )
    )


def _team(db: Session, project: Project) -> ProjectTeamRepository:
    return ProjectTeamRepository(db, firm_id=project.firm_id, project_id=project.id)


def _check_candidate(db: Session, project: Project, account_id: int, role_code: str) -> None:
    """May this person hold this role on this work? Refuses before anything is written.

    Two rules, both about the person rather than about the seat:

    An inactive roster row is refused even though the database would accept the
    write. ADR-002 section 2: the firm layer is the door to the project layer, so
    the row would grant nothing — and if the role asked for is lead, it would do
    real harm, since uq_project_member_lead counts an inert row and the work
    would be left with a responsible who cannot open it.

    A firm client may only ever be a project client (section 11.2). The roster
    holds the mirror of this rule: HU-2 refuses to make someone a firm client
    while they hold a non-client project role. Together the two keep the role
    systems agreeing whichever side the change comes from.
    """
    firm_role = firm_role_code(db, project.firm_id, account_id)
    if firm_role is None:
        raise ProjectTeamError(NOT_ON_ROSTER)
    if firm_role == FIRM_CLIENT and role_code != CLIENT:
        raise ProjectTeamError(FIRM_CLIENT_ONLY_AS_CLIENT)


def _check_client_seat(team: ProjectTeamRepository, account_id: int) -> None:
    """A work has at most one client, and this is where a second one is refused.

    Refused and not replaced, which is the difference between this seat and the
    lead's. HU-6 spells out that assigning lead *transfers* it, and says nothing
    of the sort about the client — deliberately, because the two cases are not
    alike: the outgoing lead stays on the work as a collaborator, while an
    outgoing client cannot be demoted anywhere (a firm client may hold no other
    project role), so replacing them would silently throw them off the work.
    Making it two steps keeps that consequence in the lead's hands.

    The client is still a single source, as HU-6 asks: it is one project_member
    row, the same one HU-3's edit form writes and the same one its listing reads.
    """
    holder = team.holder(CLIENT)
    if holder is not None and holder.account_id != account_id:
        raise ProjectTeamError(ALREADY_HAS_CLIENT)


def _transfer_lead(db: Session, team: ProjectTeamRepository, to_account_id: int) -> None:
    """Free the lead seat for someone else, leaving its holder as a collaborator.

    The flush is load-bearing, exactly as in _set_client: uq_project_member_lead
    allows one lead row per work, so without it the demotion and the promotion
    reach the database together and the index refuses the pair.

    Called before the promotion and never after, so at no point in the
    transaction does the work have two leads. It cannot have none either: both
    statements are in the caller's transaction, and the route commits once.
    """
    current = team.holder(LEAD)
    if current is None or current.account_id == to_account_id:
        return

    demoted = project_role(db, DEMOTED_LEAD)
    current.role_id = demoted.id
    current.role_code = demoted.code
    db.flush()


def add_team_member(
    db: Session, project: Project, *, account_id: int, role_code: AssignableProjectRole
) -> ProjectMember:
    """Put someone from the firm's roster on this work, with one role.

    Refused with ProjectTeamError, before anything is written, when the person is
    not an active member of the firm, is already on this team, is a firm client
    asked to be anything but the client, or would be a second client.

    Asking for lead transfers it: HU-6 has no separate "transfer" action, because
    a work always has a responsible and appointing a new one is the only way the
    old one stops being it.
    """
    team = _team(db, project)
    if team.get(account_id) is not None:
        raise ProjectTeamError(ALREADY_ON_TEAM)

    _check_candidate(db, project, account_id, role_code)
    if role_code == CLIENT:
        _check_client_seat(team, account_id)

    if role_code == LEAD:
        _transfer_lead(db, team, account_id)

    assign_role(db, project, account_id, role_code)
    db.flush()

    member = team.get(account_id)
    if member is None:
        raise RuntimeError(f"assignment of account {account_id} vanished right after being written")
    return member


def change_team_role(
    db: Session,
    project: Project,
    *,
    actor_id: int,
    account_id: int,
    role_code: AssignableProjectRole,
) -> ProjectMember:
    """Give someone already on this work another role on it.

    The checks, in the order they run:

    - nobody with that account on this work: TeamMemberNotFoundError;
    - they already hold it: nothing to do, and answering 200 with the row makes
      a double-submitted form harmless;
    - they are the lead and are being moved off it: refused. Demoting the lead
      directly is the one way to leave a work with nobody responsible, and HU-6
      forbids it. The way out is to give lead to someone else, which transfers it;
    - the candidate rules, re-checked because a person's firm role can change
      while the section is open;
    - a second client, refused as on the add.

    actor_id is not read here. It is taken so the signature matches the other two
    writes and so the rule "you cannot promote yourself" has an obvious home if
    a story ever asks for it; today the only role that could do so is the lead's
    own, and a lead already holds it.
    """
    team = _team(db, project)
    member = team.get(account_id)
    if member is None:
        raise TeamMemberNotFoundError

    if member.role_code == role_code:
        return member

    if member.role_code == LEAD:
        raise ProjectTeamError(LEAD_IS_TRANSFERRED)

    _check_candidate(db, project, account_id, role_code)
    if role_code == CLIENT:
        _check_client_seat(team, account_id)

    if role_code == LEAD:
        _transfer_lead(db, team, account_id)

    role = project_role(db, role_code)
    member.role_id = role.id
    member.role_code = role.code
    db.flush()
    return member


def remove_team_member(db: Session, project: Project, *, actor_id: int, account_id: int) -> None:
    """Take someone off this work. A real DELETE, and the one in the project.

    Nothing is logically deleted because there is nothing to deactivate:
    project_member carries no is_active by design (ADR-002 section 11.3), and the
    team rule about logical deletion is about the entities of the ABM — the work
    itself is archived, never deleted — while an assignment is not one of them.
    services/project.py already removes a client this way when the edit form
    clears it.

    Whoever is taken off stops seeing the work on their next request: permissions
    are resolved against the database every time and never from the token
    (ADR-002 section 9), which is what HU-6 means by "deja de ver la obra
    inmediatamente".

    The lead cannot be removed, by themselves or by anyone: the work would be
    left with nobody responsible. Two messages for the one rule, because "you are
    the lead" and "they are the lead" are different situations to be in.
    """
    team = _team(db, project)
    member = team.get(account_id)
    if member is None:
        raise TeamMemberNotFoundError

    if member.role_code == LEAD:
        raise ProjectTeamError(
            CANNOT_LEAVE_AS_LEAD if account_id == actor_id else LEAD_IS_TRANSFERRED
        )

    db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.account_id == account_id,
        )
    )
    db.flush()
