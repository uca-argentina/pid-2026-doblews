"""What platform support does to firms and accounts (HU-7).

Plain functions over the session, like roster.py: they return data, flush and
never commit, and a broken rule is an exception of this module rather than an
HTTPException. The route owns the transaction and the status codes.

Support administers accounts, never content (ADR-002 section 7), and nothing
here reads a project, a take-off or a roster beyond counting it. Nor does
anything go through the firm-scoped repositories: support acts on the platform
as a whole, and a firm_id filter would be the wrong question to ask here.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Account, Firm, FirmMember
from app.services.roster import OWNER, firm_role, is_staff

# What support reads when a rule says no. Spanish, because they are rendered as
# they are, and constants so the tests assert against these very strings.
STAFF_CANNOT_OWN = "Una cuenta de soporte no puede ser propietaria de un estudio"
INACTIVE_ACCOUNT_CANNOT_OWN = (
    "Esa cuenta está dada de baja en la plataforma: no podría entrar a su estudio"
)


class PlatformError(Exception):
    """A platform rule refused the change. Nothing was written.

    Carries the message support reads, so the route passes it through as is.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class FirmNotFoundError(Exception):
    """No firm with that id on the platform."""


class AccountNotFoundError(Exception):
    """No account support may reset: the address is unknown, or it is staff.

    One error for both, because the answer to support is the same: there is no
    account here you can act on.
    """


@dataclass(frozen=True)
class FirmAdminEntry:
    """One firm as support's listing renders it: its data and a head count.

    The count and nothing else about the roster. Who works in a firm is the
    owner's business; support only needs to tell a live firm from an empty one.
    """

    id: int
    name: str
    contact_email: str
    phone: str | None
    is_active: bool
    created_at: datetime
    member_count: int


class CreatedFirm(NamedTuple):
    """What create_firm made, and what it found already there.

    owner_existed is the one fact the route cannot work out on its own. Comparing
    the stored name with the typed one guesses wrong exactly when support typed
    the person's real name, which is when it matters most: the typed password
    was ignored, and support is about to hand it over.
    """

    firm: Firm
    owner: Account
    owner_existed: bool


def _entry_query() -> Select:
    """The one definition of a firm as support sees it, for the list and for one.

    member_count counts active roster rows only: the people who left are not
    working there. An outer join, so a firm whose roster emptied out still shows
    up with 0. The count goes over firm_member.account_id and not over *, which
    would count the one all-NULL row the outer join produces for such a firm.
    """
    return (
        select(
            Firm.id,
            Firm.name,
            Firm.contact_email,
            Firm.phone,
            Firm.is_active,
            Firm.created_at,
            func.count(FirmMember.account_id),
        )
        .outerjoin(FirmMember, (FirmMember.firm_id == Firm.id) & FirmMember.is_active)
        .group_by(Firm.id)
    )


def list_firms(db: Session) -> list[FirmAdminEntry]:
    """Every firm on the platform, suspended ones included, ordered by name.

    Suspended firms are part of the answer because the listing is where support
    finds one to reactivate.
    """
    rows = db.execute(_entry_query().order_by(Firm.name, Firm.id)).all()
    return [FirmAdminEntry(*row) for row in rows]


def get_firm(db: Session, firm_id: int) -> FirmAdminEntry:
    """One firm as the listing shows it, so a write can answer with its new row."""
    row = db.execute(_entry_query().where(Firm.id == firm_id)).first()
    if row is None:
        raise FirmNotFoundError
    return FirmAdminEntry(*row)


def create_firm(
    db: Session,
    *,
    name: str,
    contact_email: str,
    phone: str | None,
    owner_name: str,
    owner_email: str,
    owner_password: str,
) -> CreatedFirm:
    """Create a firm together with its owner, in the caller's transaction.

    ADR-002 section 10: a firm without an owner is a firm nobody can enter, so
    it cannot exist even for an instant. Both rows are flushed together and the
    route commits once; if anything here raises, neither is written.

    The owner's account:

    - no account with that address: one is created with the typed name and
      password, which support hands over in person;
    - an account exists (the person works with another firm): it becomes the
      owner as it is, and the typed name and password are ignored — they are
      that person's, not support's to overwrite. HU-7: "se lo asigna como
      propietario sin crear una cuenta nueva";
    - it is platform staff: refused, ADR-002 section 11.4. Support cannot hand
      itself a firm role, and staff and firm members stay separate populations;
    - it is deactivated on the platform: refused, because it could not log in
      and the new firm would be one nobody can enter after all.

    Returns the account and whether it already existed, so the route can say
    so: when it did, the password support typed is not the one to hand over.

    `owner_email` must already be normalized; the request schema does it.
    """
    # Hashed first, on every path, as in roster.add_member. Support is trusted
    # and the timing reveals nothing it could not already see, but one rule for
    # every form that takes a first password is easier to keep than two.
    password_hash = hash_password(owner_password)
    owner_role = firm_role(db, OWNER)

    account = db.scalar(select(Account).where(Account.email == owner_email))
    owner_existed = account is not None
    if account is None:
        account = Account(name=owner_name, email=owner_email, password_hash=password_hash)
        db.add(account)
    elif is_staff(db, account.id):
        raise PlatformError(STAFF_CANNOT_OWN)
    elif not account.is_active:
        raise PlatformError(INACTIVE_ACCOUNT_CANNOT_OWN)

    firm = Firm(name=name, contact_email=contact_email, phone=phone)
    db.add(firm)
    db.flush()  # assigns the ids the roster row needs

    db.add(FirmMember(firm_id=firm.id, account_id=account.id, role_id=owner_role.id))
    db.flush()
    return CreatedFirm(firm=firm, owner=account, owner_existed=owner_existed)


def set_firm_active(db: Session, firm_id: int, *, is_active: bool) -> Firm:
    """Suspend or reactivate a firm. A logical change: nothing is deleted.

    Only firm.is_active moves. Locking the members out is already done by the
    one query that decides where a person may act (auth._membership_query), so
    a suspended firm vanishes from /auth/me and answers 404 to every firm route
    on its members' very next request. Reactivating brings everything back as
    it was: roster, projects and take-offs never changed.

    Idempotent: suspending a suspended firm is not an error, it is already in
    the state support asked for.
    """
    firm = db.get(Firm, firm_id)
    if firm is None:
        raise FirmNotFoundError

    firm.is_active = is_active
    db.flush()
    return firm


def reset_password(db: Session, *, email: str, password: str) -> None:
    """Give an account a new password, typed by support and handed over in person.

    HU-7 and no more: there is no recovery email and no forced change on the
    next login. The account's is_active is not touched, so resetting does not
    quietly bring back someone deactivated.

    Staff accounts are refused, and refused as if they did not exist. A
    platform_member row is the most powerful thing in the system and no endpoint
    writes one (ADR-002 section 5); being able to reset another support's
    password would be a way into that power without writing one.

    `email` must already be normalized; the request schema does it.
    """
    account = db.scalar(select(Account).where(Account.email == email))
    if account is None or is_staff(db, account.id):
        raise AccountNotFoundError

    account.password_hash = hash_password(password)
    db.flush()
