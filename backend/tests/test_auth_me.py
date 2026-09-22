"""GET /auth/me: the session the frontend boots from.

Two things are being proved here. That identity is re-read from the database on
every request and not taken from the token (ADR-002 section 9), and that the
list of firms is exactly the set of doors that are actually open.
"""

from sqlalchemy import text

from app.core.token import create_access_token


def me(client, headers):
    return client.get("/auth/me", headers=headers)


def test_without_a_token_it_refuses_and_names_the_scheme(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    # RFC 7235 requires it on a 401, and it is what stops FastAPI's default
    # HTTPBearer behaviour of answering 403 from reaching the frontend, which
    # reads 403 as "logged in but not allowed".
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_garbage_token_is_refused(client):
    assert me(client, {"Authorization": "Bearer not-a-token"}).status_code == 401


def test_token_for_an_account_that_no_longer_exists_is_refused(client):
    assert me(client, {"Authorization": f"Bearer {create_access_token(999999)}"}).status_code == 401


def test_deactivating_an_account_takes_effect_on_the_next_request(client, db, world, auth_header):
    """The promise of ADR-002 section 9, and the reason permissions are not in
    the token: the token stays valid, the person does not."""
    headers = auth_header(world.account_a)
    assert me(client, headers).status_code == 200

    db.execute(text("UPDATE account SET is_active = false WHERE id = :id"), {"id": world.account_a})

    assert me(client, headers).status_code == 401


def test_reports_the_account_and_its_firm_with_the_role_label(client, world, auth_header):
    body = me(client, auth_header(world.account_a)).json()

    assert body["id"] == world.account_a
    assert body["email"] == "ana@test.com"
    assert body["platform_roles"] == []
    # An owner holds plenty of firm permissions and none of the platform's.
    assert body["platform_permissions"] == []
    assert body["firms"] == [
        {
            "id": world.firm_a,
            "name": "norte",
            # The Spanish label comes from role.name in the seed, so the
            # frontend never keeps its own code -> label dictionary.
            "role": {"code": "owner", "name": "Propietario"},
        }
    ]


def test_someone_in_two_firms_sees_both_ordered_by_name(client, db, world, role_id, auth_header):
    db.execute(
        text(
            "INSERT INTO firm_member (firm_id, account_id, role_id, role_scope)"
            " VALUES (:f, :a, :r, 'firm')"
        ),
        {"f": world.firm_b, "a": world.account_a, "r": role_id[("client", "firm")]},
    )

    body = me(client, auth_header(world.account_a)).json()

    assert [firm["name"] for firm in body["firms"]] == ["norte", "sur"]
    assert [firm["role"]["code"] for firm in body["firms"]] == ["owner", "client"]


def test_leaving_a_roster_hides_that_firm(client, db, world, auth_header):
    """firm_member.is_active: the person still logs in, this firm just stops
    existing for them."""
    db.execute(
        text("UPDATE firm_member SET is_active = false WHERE account_id = :a"),
        {"a": world.account_a},
    )

    body = me(client, auth_header(world.account_a)).json()

    assert body["firms"] == []


def test_a_suspended_firm_hides_itself_from_its_own_owner(client, db, world, auth_header):
    """firm.is_active: HU-7 says a suspended firm locks its members out."""
    db.execute(text("UPDATE firm SET is_active = false WHERE id = :id"), {"id": world.firm_a})

    body = me(client, auth_header(world.account_a)).json()

    assert body["firms"] == []


def test_an_account_with_no_firms_is_a_valid_session(client, db, auth_header):
    """ADR-002 section 11.6: a person with no assignment logs in fine and has
    nothing to see. The UI owes them an explanation, not an error."""
    account_id = db.execute(
        text(
            "INSERT INTO account (name, email, password_hash)"
            " VALUES ('Nadie', 'nadie@test.com', 'x') RETURNING id"
        )
    ).scalar_one()

    response = me(client, auth_header(account_id))

    assert response.status_code == 200
    assert response.json()["firms"] == []


def test_support_is_reported_by_its_platform_role(client, db, role_id, auth_header):
    """So the frontend can land support somewhere other than "you belong to no
    firm yet", which is the wrong message for the account that creates firms."""
    account_id = db.execute(
        text(
            "INSERT INTO account (name, email, password_hash)"
            " VALUES ('Soporte', 'soporte@test.com', 'x') RETURNING id"
        )
    ).scalar_one()
    db.execute(
        text(
            "INSERT INTO platform_member (account_id, role_id, role_scope)"
            " VALUES (:a, :r, 'platform')"
        ),
        {"a": account_id, "r": role_id[("support", "platform")]},
    )

    body = me(client, auth_header(account_id)).json()

    assert body["platform_roles"] == ["support"]
    assert body["firms"] == []


def test_support_gets_its_platform_permissions_sorted(client, db, role_id, auth_header):
    """HU-7: the frontend opens the support screens with can("firm.create"),
    never by reading the role, so the grants have to travel with the session."""
    account_id = db.execute(
        text(
            "INSERT INTO account (name, email, password_hash)"
            " VALUES ('Soporte', 'soporte@test.com', 'x') RETURNING id"
        )
    ).scalar_one()
    db.execute(
        text(
            "INSERT INTO platform_member (account_id, role_id, role_scope)"
            " VALUES (:a, :r, 'platform')"
        ),
        {"a": account_id, "r": role_id[("support", "platform")]},
    )

    permissions = me(client, auth_header(account_id)).json()["platform_permissions"]

    assert {"firm.create", "firm.view", "firm.suspend", "account.reset_password"} <= set(
        permissions
    )
    assert permissions == sorted(permissions)
    # ADR-002 section 7: support administers accounts, never content.
    assert not [code for code in permissions if code.startswith("project.")]
