"""What the API says about the people on a firm's roster (HU-2)."""

from datetime import datetime
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.core.security import MAX_PASSWORD_BYTES
from app.schemas.firm import RoleOut
from app.services.roster import AssignableFirmRole


def _normalize_email(value: str) -> str:
    """Validate an address and return it the way account stores it.

    The same library and the same checks as Pydantic's EmailStr, with one
    difference: test_environment=True lets the .test domain through. EmailStr
    refuses it as a special-use name, and the development seed lives there
    (ana@estudionorte.test, bruno@estudiosur.test), so with EmailStr the demo
    could not add Bruno to a second firm — the very case HU-2 is about.
    Accepting it in production costs nothing: .test is reserved by RFC 6761, no
    real person has one, and this application sends no email. The same flag
    also skips the DNS lookup, which EmailStr skips as well.

    Lowercased whole, not only the domain as the library does, because account
    carries CHECK (email = lower(email)): an address with a capital in it would
    never match a lookup, and could not be inserted at all.
    """
    try:
        validated = validate_email(value.strip(), check_deliverability=False, test_environment=True)
    except EmailNotValidError as error:
        raise ValueError(str(error)) from None
    return validated.normalized.lower()


Email = Annotated[str, AfterValidator(_normalize_email)]


def _fits_bcrypt(value: str) -> str:
    """bcrypt's limit is in bytes, and Field(max_length=) counts characters.

    Checked here so the caller gets a 422 naming the field, rather than the
    PasswordTooLongError that core/security.py raises as a last line of defence
    surfacing as a 500.
    """
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"la contraseña no puede superar los {MAX_PASSWORD_BYTES} bytes")
    return value


# A password someone types for another person and hands over in person: the
# owner for a new member (HU-2), support for a new owner or a reset (HU-7).
# Never stripped, since a space is a legitimate character in a password.
TypedPassword = Annotated[str, Field(min_length=8), AfterValidator(_fits_bcrypt)]


class MemberOut(BaseModel):
    """One row of the roster listing.

    Keyed by account_id because that is what identifies a member inside a firm:
    firm_member's primary key is (firm_id, account_id), and the firm already
    comes from the URL.
    """

    account_id: int
    # From the global account, not from this firm. The owner cannot edit either:
    # they are the person's identity everywhere, not a detail of this roster.
    name: str
    email: str
    role: RoleOut
    # Roster state, not account state: False means they left this firm and can
    # still log in and work in any other.
    is_active: bool
    joined_at: datetime


class MemberCreate(BaseModel):
    """The add form: who, with which role, and their first password.

    Adding someone whose address already has an account adds that account to
    the roster and ignores name and password, which stay the person's own.
    Adding someone who left brings them back. The response is the same in all
    three cases (HU-2: never reveal whether an account exists).
    """

    # Same limit as account.name. Stripped, so "   " is empty and refused.
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    email: Email
    # owner is not in the Literal, so asking for it is a 422 before any code runs.
    role_code: AssignableFirmRole
    # Typed by the owner, who hands it over in person: HU-2 has no invitation
    # email and no password recovery.
    password: TypedPassword


class MemberRoleUpdate(BaseModel):
    """The edit form: the role, and nothing else.

    No email and no name. HU-2: "el email no se edita — es su identidad global,
    no un dato de mi estudio", and the name belongs to the same account. A body
    that sends them anyway is not refused; the fields are simply never read.
    """

    role_code: AssignableFirmRole
