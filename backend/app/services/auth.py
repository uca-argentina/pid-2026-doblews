"""Who this person is, and which firms they may act in.

Plain functions over the session: they return None or an empty list and never
raise HTTPException, so they can be tested without HTTP and reused from a script
or a future CLI. Turning "nothing found" into a status code is the API layer's
job, in app/api/deps.py.
"""

import secrets
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import Account, Firm, FirmMember, PlatformMember, Role

# A real hash of a password nobody knows, used to spend the same ~250 ms on a
# login for an address that does not exist. Without it, "no such email" answers
# in about 2 ms and "wrong password" in about 250: two orders of magnitude,
# measurable with curl, which turns the login form into a user enumerator. Both
# HU-1 and HU-2 promise not to reveal whether an account exists.
#
# Generated at import rather than pinned as a literal: a hardcoded hash would
# keep whatever cost factor was current the day it was written, and the timings
# would drift apart again the day bcrypt's default goes up.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@dataclass(frozen=True)
class FirmMembership:
    """A person's roster row in one firm, with the labels the UI renders.

    Carries role_id, not just the code, so that T-03 can resolve permissions
    from the same row instead of querying for the role a second time.
    """

    firm_id: int
    firm_name: str
    role_id: int
    role_code: str
    role_name: str


def authenticate(db: Session, email: str, password: str) -> Account | None:
    """Return the account these credentials belong to, or None.

    One None for all three failures — unknown address, wrong password, and
    deactivated account — because the caller must answer all three identically.
    Saying "your account is disabled" would confirm that the address exists,
    which is the one thing HU-1 asks us not to reveal.
    """
    account = db.scalar(select(Account).where(Account.email == email))

    if account is None or not account.is_active:
        # Deliberately wasted work: see _DUMMY_HASH. Skipping it here is what
        # reintroduces the timing oracle.
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, account.password_hash):
        return None

    return account


def _membership_query():
    """The one definition of "a firm this person can act in".

    Both callers below build on this, and they must stay identical: if they ever
    drift, the picker offers a firm that the request guard then rejects with a
    404, which reads as a bug in the app rather than as the roster change it is.

    Both is_active flags are load-bearing and mean different things. The roster
    one is the person leaving this firm (ADR-002 section 5); the firm one is
    support suspending the whole firm, which HU-7 says must lock its members out.
    """
    return (
        select(Firm.id, Firm.name, Role.id, Role.code, Role.name)
        .join(FirmMember, FirmMember.firm_id == Firm.id)
        # Matching on role.id alone is enough: it is the primary key, and the
        # composite foreign key on firm_member already guarantees the scope is
        # 'firm'. Repeating that condition here would read as if it filtered.
        .join(Role, Role.id == FirmMember.role_id)
        .where(FirmMember.is_active, Firm.is_active)
    )


def list_firm_memberships(db: Session, account_id: int) -> list[FirmMembership]:
    """Every firm this person may act in, for the picker and for /auth/me.

    An empty list is a valid answer, not an error: ADR-002 section 11.6 asks the
    UI for a screen that explains it. Ordered by name so the picker does not
    reshuffle between reloads. Served by ix_firm_member_account_id.
    """
    rows = db.execute(
        _membership_query().where(FirmMember.account_id == account_id).order_by(Firm.name)
    ).all()
    return [FirmMembership(*row) for row in rows]


def get_firm_membership(db: Session, account_id: int, firm_id: int) -> FirmMembership | None:
    """The roster row for one firm, or None if this person cannot act in it.

    None covers four different situations on purpose — never a member, left the
    roster, firm suspended, firm does not exist — because the caller answers all
    four with the same 404. Telling them apart would confirm that a firm exists.
    """
    row = db.execute(
        _membership_query().where(
            FirmMember.account_id == account_id,
            FirmMember.firm_id == firm_id,
        )
    ).first()
    return FirmMembership(*row) if row is not None else None


def list_platform_roles(db: Session, account_id: int) -> list[str]:
    """Platform role codes, which in practice means ["support"] or [].

    For painting the UI only: it is what stops the support account, who belongs
    to no firm, from landing on "you do not belong to any firm yet" — a message
    that would be plainly wrong for the account that creates firms. Nothing is
    authorized with this (ADR-002: the code checks permissions, never roles).
    """
    return list(
        db.scalars(
            select(Role.code)
            .join(PlatformMember, PlatformMember.role_id == Role.id)
            .where(PlatformMember.account_id == account_id)
            .order_by(Role.code)
        )
    )
