"""What the token module accepts and, mostly, what it refuses."""

from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.token import create_access_token, decode_access_token


@pytest.fixture
def settings():
    return get_settings()


def test_round_trip_returns_the_same_account():
    assert decode_access_token(create_access_token(42)) == 42


def test_subject_is_encoded_as_a_string(settings):
    """RFC 7519 types sub as StringOrURI, and PyJWT rejects a numeric one."""
    payload = jwt.decode(
        create_access_token(42),
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == "42"


def test_expired_token_is_refused():
    assert decode_access_token(create_access_token(42, timedelta(minutes=-1))) is None


def test_token_signed_with_another_secret_is_refused(settings):
    forged = jwt.encode({"sub": "42", "exp": 9999999999}, "another-secret", algorithm="HS256")
    assert decode_access_token(forged) is None


def test_unsigned_token_is_refused():
    """The canonical JWT attack: strip the signature and claim alg is none.

    Only fails to work because decode passes an explicit algorithm list instead
    of believing the token's own header.
    """
    unsigned = jwt.encode({"sub": "42", "exp": 9999999999}, key="", algorithm="none")
    assert decode_access_token(unsigned) is None


def test_token_without_expiry_is_refused(settings):
    """A token with no exp would be a session that never ends."""
    endless = jwt.encode({"sub": "42"}, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    assert decode_access_token(endless) is None


def test_token_without_subject_is_refused(settings):
    anonymous = jwt.encode(
        {"exp": 9999999999}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    assert decode_access_token(anonymous) is None


def test_non_numeric_subject_is_refused(settings):
    """What a token minted by something else would look like."""
    foreign = jwt.encode(
        {"sub": "not-an-id", "exp": 9999999999},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(foreign) is None


def test_garbage_is_refused():
    assert decode_access_token("not-a-token") is None
