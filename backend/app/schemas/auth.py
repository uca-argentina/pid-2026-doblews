"""The shapes the login and session endpoints speak in."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.firm import FirmSummary


class LoginRequest(BaseModel):
    """Credentials as the login form sends them."""

    email: str
    # A generous ceiling, not bcrypt's 72-byte limit: that rule belongs to
    # core/security.py, which already fails closed, and login only ever verifies
    # a password — it never hashes one. Repeating the limit here would also
    # restate it in the wrong unit, since Pydantic counts characters and bcrypt
    # counts bytes.
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: str) -> str:
        """Lowercase and trim, because the column is stored that way.

        account carries CHECK (email = lower(email)), so every address in the
        database is already lowercased and a lookup for "Ana@Test.com" would
        match nothing. Normalizing here rather than in the endpoint means every
        future form that takes an email inherits it.
        """
        return value.strip().lower()


class TokenResponse(BaseModel):
    """What a successful login returns, and the whole of it.

    No expires_in: without refresh tokens the frontend has nothing to schedule.
    The only thing it could do with that number is log the user out early, and
    the 401 interceptor already covers the case.
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class MeResponse(BaseModel):
    """Who is logged in and where they can act — the frontend's session state.

    Flat rather than wrapping the person in an "account" key: on /auth/me the
    top-level object is the account, and the wrapper would buy nothing.

    Deliberately carries no permission list. Resolving permissions is T-03's
    job, and shipping a half-resolved set now would invite the frontend to
    branch on it before the engine that fills it exists.
    """

    id: int
    name: str
    email: str

    # A list and not an is_support flag: platform_member keeps role_id inside
    # its primary key precisely so one person can hold several platform roles,
    # and a boolean would need a contract change the day a second one appears.
    # Empty for everyone except support.
    platform_roles: list[str]

    # Only the firms whose roster row and firm are both active. Empty is a valid
    # state, not an error: ADR-002 section 11.6 asks for a screen that explains
    # it rather than an empty list or a failure.
    firms: list[FirmSummary]
