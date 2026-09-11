"""The rules for changing who is on a firm's roster (HU-2).

Plain functions over the session, like the rest of the services: they return
data and never raise HTTPException. A broken rule is a RosterError, and turning
it into a status code is the API layer's job.

They flush and never commit. The route that calls them owns the transaction,
so a service can run inside a larger one: HU-7 creates a firm and its owner in
a single transaction, and "find or create the account" is the same step there.
"""

from typing import Literal, get_args

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Account, FirmMember, PlatformMember, Role
from app.repositories.member import FirmMemberRepository

# The firm roles an owner may hand out, and the one place that leaves owner out.
# A second owner would break "exactly one active owner per firm" (ADR-002
# section 11.1), and transferring ownership is out of HU-2's scope. Keeping
# owner out of every add and every edit is what makes that invariant hold by
# construction instead of by checking.
#
# A Literal rather than a list so the request schemas can use it as a field
# type: asking for owner is then a 422 from Pydantic before any code runs.
AssignableFirmRole = Literal["architect", "client"]

# The firm role whose holders may only ever be clients on a project
# (ADR-002 section 11.2). Named apart from the project role of the same code:
# they are two different roles that happen to share a word.
FIRM_CLIENT = "client"

# Compared by code for an invariant, not for authorization: "exactly one active
# owner per firm" (ADR-002 section 11.1) is a rule about the data, and section
# 11 sends it to this layer by name. Who may edit the roster at all is still
# decided by the member.* permissions, never here.
OWNER = "owner"

# What the owner reads when a rule says no. Spanish, because they are rendered
# as they are, and constants so the tests assert against these very strings.
ALREADY_MEMBER = "Esta persona ya es miembro del estudio"
STAFF_ACCOUNT = "Esta cuenta no puede sumarse a un estudio"
CLIENT_WITH_PROJECT_ROLES = (
    "Esta persona tiene en obras del estudio un rol que un cliente no puede tener. "
    "Sacala de esas obras antes de hacerla cliente."
)
CANNOT_CHANGE_OWN_ROLE = "No podés cambiar tu propio rol"
OWNER_ROLE_IS_FIXED = "El rol de propietario no se puede cambiar"
CANNOT_REMOVE_YOURSELF = "No podés darte de baja a vos mismo"
OWNER_CANNOT_BE_REMOVED = "El propietario no se puede dar de baja"
LEADS_ACTIVE_PROJECTS = (
    "Esta persona es responsable de obras activas del estudio. "
    "Transferí esa responsabilidad antes de darla de baja."
)


class RosterError(Exception):
    """A roster rule refused the change. Nothing was written.

    Carries the message the owner reads, so the route passes it through
    without keeping a second table of texts.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class MemberNotFoundError(Exception):
    """No active member with that account in this firm.

    One error for "never on this roster", "on another firm's roster", "left"
    and "no such account", because the API answers all of them with the same
    404 and must not hint at which one it was.
    """


def list_assignable_roles(db: Session) -> list[Role]:
    """The firm roles the add and edit forms offer, with their seeded labels.

    Read from the role table rather than written out here, so the labels are
    the ones the seed holds and the frontend keeps no dictionary of its own.
    No firm filter: the catalogue is the same for every firm (ADR-002 section 4).
    """
    return list(
        db.scalars(
            select(Role)
            .where(Role.scope == "firm", Role.code.in_(get_args(AssignableFirmRole)))
            .order_by(Role.code)
        )
    )


def _firm_role(db: Session, code: str) -> Role:
    """The seeded firm role with this code. Missing means a broken seed: a 500."""
    return db.scalars(select(Role).where(Role.scope == "firm", Role.code == code)).one()


def _is_staff(db: Session, account_id: int) -> bool:
    return bool(db.scalar(select(exists().where(PlatformMember.account_id == account_id))))


def add_member(
    db: Session,
    firm_id: int,
    *,
    name: str,
    email: str,
    role_code: AssignableFirmRole,
    password: str,
) -> FirmMember:
    """Put a person on this firm's roster, creating their account if needed.

    Three cases, one answer. HU-2 promises the add never reveals whether an
    address already has an account on the platform, so:

    - no account yet: one is created with the name and password the owner typed;
    - an account exists (they work with another firm): it joins the roster as
      it is, and the typed name and password are ignored — they are that
      person's, not this firm's to overwrite;
    - they were on this roster and left: their row comes back with the new
      role, and with it every project assignment they had, untouched (ADR-002
      section 11.3). Reinstating is an add; there is no endpoint of its own.

    Refused with RosterError, before anything is written, when they are already
    an active member, when the account is platform staff (ADR-002 section 11.4:
    support is a separate population), or when coming back as a firm client
    while still holding a non-client project role (section 11.2).

    `email` must already be normalized; the request schema does it.
    """
    # Hashed first, on every path. bcrypt takes ~250 ms on purpose, so hashing
    # only when an account is created would make "new address" measurably slower
    # than "existing address" — the enumeration oracle _DUMMY_HASH closes on the
    # login, reopened here.
    password_hash = hash_password(password)
    role = _firm_role(db, role_code)

    account = db.scalar(select(Account).where(Account.email == email))
    if account is None:
        account = Account(name=name, email=email, password_hash=password_hash)
        db.add(account)
        db.flush()  # assigns the id the roster row needs
    elif _is_staff(db, account.id):
        raise RosterError(STAFF_ACCOUNT)

    members = FirmMemberRepository(db, firm_id=firm_id)
    member = members.get(account.id, include_inactive=True)

    if member is None:
        member = FirmMember(firm_id=firm_id, account_id=account.id, role_id=role.id)
        db.add(member)
    elif member.is_active:
        raise RosterError(ALREADY_MEMBER)
    else:
        if role_code == FIRM_CLIENT and members.has_non_client_project_roles(account.id):
            raise RosterError(CLIENT_WITH_PROJECT_ROLES)
        # joined_at is kept: this is the same membership coming back, and the
        # project rows hanging off it never left.
        member.is_active = True
        member.role_id = role.id

    db.flush()
    return member


def change_member_role(
    db: Session,
    firm_id: int,
    *,
    actor_id: int,
    account_id: int,
    role_code: AssignableFirmRole,
) -> FirmMember:
    """Give an active member of this firm another firm role.

    Only the role changes. The email is the person's global identity and HU-2
    keeps it out of the firm's reach, and so is the name.

    The checks, in the order they run:

    - no active member with that account here: MemberNotFoundError;
    - it is the caller themselves: HU-2 and ADR-002 section 11.5, nobody takes
      away the role that gives them access;
    - it is the owner: owner is never assigned, so it is never taken away
      either, and that is what keeps exactly one active owner per firm
      (section 11.1). Today only the owner holds member.edit_role, so this and
      the previous check are the same case. They are kept apart for the day a
      firm_admin role gets member.edit_role (ADR-002, pending review): then the
      owner stops being covered by "not yourself";
    - becoming a firm client while holding a non-client project role
      (section 11.2): refused rather than downgrading their project roles here,
      which would break "one client per project" and "never without a lead".
    """
    members = FirmMemberRepository(db, firm_id=firm_id)
    member = members.get(account_id)
    if member is None:
        raise MemberNotFoundError

    if account_id == actor_id:
        raise RosterError(CANNOT_CHANGE_OWN_ROLE)
    if member.role_id == _firm_role(db, OWNER).id:
        raise RosterError(OWNER_ROLE_IS_FIXED)
    if role_code == FIRM_CLIENT and members.has_non_client_project_roles(account_id):
        raise RosterError(CLIENT_WITH_PROJECT_ROLES)

    member.role_id = _firm_role(db, role_code).id
    db.flush()
    return member


def remove_member(db: Session, firm_id: int, *, actor_id: int, account_id: int) -> None:
    """Take an active member off this firm's roster. A logical removal.

    Only firm_member.is_active changes. The account is untouched, so they keep
    logging in and working in any other firm. Their project_member rows are
    untouched too: without an active roster row they grant nothing (ADR-002
    section 2), and if they are ever added back they work again as they were
    (section 11.3). Nothing is deleted.

    The checks, in the order they run:

    - no active member with that account here: MemberNotFoundError;
    - it is the caller themselves: ADR-002 section 11.5;
    - it is the owner: a firm always has exactly one active owner (section
      11.1). Same case as the previous one today, kept apart for the same
      reason as in change_member_role;
    - they lead a live project of this firm: their lead row would go inert but
      still count for uq_project_member_lead, leaving the project with no
      working lead and no way to appoint one. The lead is transferred first
      (HU-6). Archived projects do not block it.
    """
    members = FirmMemberRepository(db, firm_id=firm_id)
    member = members.get(account_id)
    if member is None:
        raise MemberNotFoundError

    if account_id == actor_id:
        raise RosterError(CANNOT_REMOVE_YOURSELF)
    if member.role_id == _firm_role(db, OWNER).id:
        raise RosterError(OWNER_CANNOT_BE_REMOVED)
    if members.leads_active_projects(account_id):
        raise RosterError(LEADS_ACTIVE_PROJECTS)

    member.is_active = False
    db.flush()
