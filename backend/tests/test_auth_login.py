"""POST /auth/login: what gets in, and what every refusal looks like.

The point of most of these is that the failures are indistinguishable. HU-1 and
HU-2 both promise the login never reveals whether an address has an account.
"""

from sqlalchemy import text

from app.api.routes.auth import INVALID_CREDENTIALS
from app.core.token import decode_access_token


def login(client, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_valid_credentials_return_a_token_for_that_account(client, world, usable_passwords):
    response = login(client, "ana@test.com", usable_passwords)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]) == world.account_a


def test_wrong_password_is_refused(client, world, usable_passwords):
    response = login(client, "ana@test.com", "not-the-password")

    assert response.status_code == 401
    assert response.json()["detail"] == INVALID_CREDENTIALS


def test_unknown_email_is_indistinguishable_from_a_wrong_password(client, world, usable_passwords):
    """The test that keeps the login from being a user enumerator.

    Compared against each other rather than against a literal, so the two can
    never drift apart while both still match some expected string.
    """
    unknown = login(client, "nobody@test.com", "not-the-password")
    wrong = login(client, "ana@test.com", "not-the-password")

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_deactivated_account_is_indistinguishable_too(client, db, world, usable_passwords):
    """Saying "your account is disabled" would confirm the address exists."""
    db.execute(text("UPDATE account SET is_active = false WHERE id = :id"), {"id": world.account_a})

    disabled = login(client, "ana@test.com", usable_passwords)
    unknown = login(client, "nobody@test.com", usable_passwords)

    assert disabled.status_code == 401
    assert disabled.json() == unknown.json()


def test_email_case_does_not_matter(client, world, usable_passwords):
    """account carries CHECK (email = lower(email)), so every stored address is
    lowercased and a mixed-case lookup would match nothing without the schema's
    field validator."""
    assert login(client, "ANA@Test.COM", usable_passwords).status_code == 200


def test_surrounding_whitespace_is_trimmed(client, world, usable_passwords):
    assert login(client, "  ana@test.com  ", usable_passwords).status_code == 200


def test_empty_password_is_rejected_before_reaching_the_database(client, world):
    assert login(client, "ana@test.com", "").status_code == 422


def test_absurdly_long_password_is_rejected_as_input(client, world):
    """Bounded by the schema, so no request can spend bcrypt time on 10 MB."""
    assert login(client, "ana@test.com", "x" * 5000).status_code == 422
