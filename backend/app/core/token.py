"""The only place that knows what an access token looks like.

Kept apart from security.py, which owns password hashing, because the two change
for different reasons: the hash when bcrypt's cost factor goes up, the token when
refresh tokens or key rotation arrive. Splitting them also keeps security.py free
of configuration — it stays importable without a JWT_SECRET in the environment.

No PyJWT exception crosses this boundary, so replacing the library touches this
file and nothing else. See docs/adr/0004-authentication.md.
"""

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings

# RFC 7519 calls it the "subject": who the token is about. It carries the account
# id and nothing else. Permissions are deliberately absent — they are resolved
# against the database on every request (ADR-002 section 9), so that revoking a
# role or deactivating a person takes effect immediately instead of when the
# token expires.
ACCOUNT_ID_CLAIM = "sub"


def create_access_token(account_id: int, expires_delta: timedelta | None = None) -> str:
    """Issue a token proving the bearer is this account, for a limited time.

    expires_delta is a parameter and not only a setting so tests can ask for an
    already-expired token: get_settings() is lru_cached, so patching the
    environment would never reach a process that has already read it.
    """
    settings = get_settings()
    now = datetime.now(tz=UTC)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    payload = {
        # A string, not an int: RFC 7519 types sub as StringOrURI, and PyJWT
        # rejects a numeric one outright.
        ACCOUNT_ID_CLAIM: str(account_id),
        # Costs nothing today and is the only thing that would later allow
        # "invalidate everything issued before X" without inventing a claim on
        # the spot, at a moment when every live token predates the idea.
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Return the account id the token vouches for, or None if it vouches for nothing.

    None rather than an exception, for the same reason verify_password returns
    False: every caller is an authentication path, and there an expired token, a
    forged signature and an outright malformed string all mean the same 401.
    Telling them apart would only help an attacker.

    What comes back is still just a claim about identity. ADR-002 section 9
    requires the caller to load the account and check that it is still active —
    this function cannot know that the person was deactivated a minute ago.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            # A fixed list, never the alg from the token's own header. Letting a
            # token choose how it gets verified is what the "alg: none" and
            # HMAC/RSA confusion attacks exploit. Do not simplify this away.
            algorithms=[settings.jwt_algorithm],
            # Without this a token carrying neither claim would still decode, and
            # one with no exp would be a session that never ends.
            options={"require": ["exp", ACCOUNT_ID_CLAIM]},
        )
        return int(payload[ACCOUNT_ID_CLAIM])
    except (jwt.InvalidTokenError, TypeError, ValueError):
        # InvalidTokenError is PyJWT's base for expired, forged and malformed.
        # TypeError and ValueError cover a sub that decoded fine but is not a
        # number, which is what a token minted by something else would look like.
        return None
