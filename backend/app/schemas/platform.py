"""What the API says to platform support about firms and accounts (HU-7)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, StringConstraints

from app.schemas.member import Email, TypedPassword

# Same limit as account.name and firm.name. Stripped, so "   " is empty and refused.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


def _blank_to_none(value: object) -> object:
    """An empty phone field is no phone, not a phone made of nothing.

    The form sends "" when support leaves it blank, and storing that would give
    the column two spellings of "unknown", NULL and "".
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


Phone = Annotated[
    # firm.phone is String(30).
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None,
    BeforeValidator(_blank_to_none),
]


class FirmAdminOut(BaseModel):
    """One row of support's firm listing.

    member_count and no members: who works in a firm is its owner's business,
    and support only needs to tell a live firm from an empty one (ADR-002
    section 7: support administers accounts, not content).
    """

    id: int
    name: str
    contact_email: str
    phone: str | None
    # False means suspended: nobody on its roster can act in it.
    is_active: bool
    member_count: int
    created_at: datetime


class OwnerOut(BaseModel):
    """The owner as stored, which is not always as typed.

    When the address already had an account, name is that person's own and not
    the one support typed, and so is the password.
    """

    account_id: int
    name: str
    email: str
    # True when the address already had an account, which became the owner as
    # it was. The UI needs it to tell support that the password it typed was
    # ignored and is not the one to hand over. A flag and not a name comparison,
    # which guesses wrong when support typed the person's real name. Revealing
    # it is no oracle here: only support gets this far (ADR-002 section 10.2).
    account_existed: bool


class FirmCreatedOut(FirmAdminOut):
    """The new firm, plus the owner it was created with."""

    owner: OwnerOut


class OwnerCreate(BaseModel):
    """The owner half of the create form.

    If the address already has an account, name and password are ignored: they
    belong to that person, and the account becomes the owner as it is (HU-7).
    """

    name: Name
    email: Email
    password: TypedPassword


class FirmCreate(BaseModel):
    """The create form: the firm and its first owner, which arrive together.

    One body and not two requests because ADR-002 section 10 does not allow a
    firm without an owner, not even between two calls.
    """

    name: Name
    contact_email: Email
    phone: Phone = None
    owner: OwnerCreate


class FirmStatusUpdate(BaseModel):
    """Suspend (false) or reactivate (true) a firm. The only field this edits."""

    is_active: bool


class PasswordReset(BaseModel):
    """Whose password, and the new one support hands over in person."""

    email: Email
    password: TypedPassword
