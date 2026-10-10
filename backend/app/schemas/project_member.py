"""What the API says about the people on a work's team (HU-6)."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.firm import RoleOut
from app.services.project_team import AssignableProjectRole


class ProjectMemberOut(BaseModel):
    """One row of the team section.

    Keyed by account_id because that is what identifies someone on a work:
    project_member's primary key is (project_id, account_id), and the work
    already comes from the URL.

    The same shape as MemberOut in schemas/member.py, deliberately: the two
    listings show the same person in two different rosters, and matching them
    lets the frontend render both with one component.
    """

    account_id: int
    # From the global account. The team section cannot edit either: they are the
    # person's identity everywhere, not a detail of this work.
    name: str
    email: str
    # The role on the work, not in the firm. Someone can be an architect of the
    # studio and a collaborator on this particular work.
    role: RoleOut
    # The state of their roster row, not of the assignment. False means they left
    # the firm: the seat is still theirs and comes back with them, and until then
    # it grants nothing (ADR-002 section 11.3).
    is_active: bool
    joined_at: datetime


class ProjectMemberAdd(BaseModel):
    """The add form: who, and with which role.

    An account id and not an email, like ProjectWrite.client_account_id: the
    picker is fed by this firm's roster (HU-6 — "el desplegable nunca muestra
    usuarios de otros estudios ni de la tabla global"), so the frontend already
    holds the id of everyone it may offer.
    """

    account_id: int
    # A firm-scope code like "architect" is a 422 before any code runs.
    role_code: AssignableProjectRole


class ProjectMemberRoleUpdate(BaseModel):
    """The edit form: the role on this work, and nothing else."""

    role_code: AssignableProjectRole
