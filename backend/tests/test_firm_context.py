"""GET /firms/{firm_id}: resolving the active firm from the URL.

The first isolation suite of the system, and the shape ADR-002 section 8 asks
every later endpoint to copy: one case per endpoint that reaches in from another
firm and expects a 404.

Every refusal here is a 404 and never a 403, deliberately. A 403 would confirm
the firm exists, and the existence of a competing studio's firm is itself
information we do not hand out.
"""

from sqlalchemy import text


def test_a_member_sees_their_own_firm(client, world, auth_header):
    response = client.get(f"/firms/{world.firm_a}", headers=auth_header(world.account_a))

    assert response.status_code == 200
    assert response.json() == {
        "id": world.firm_a,
        "name": "norte",
        "role": {"code": "owner", "name": "Propietario"},
    }


def test_another_firm_is_not_found(client, world, auth_header):
    """Ana owns norte. Asking for sur must look exactly like asking for a firm
    that does not exist."""
    response = client.get(f"/firms/{world.firm_b}", headers=auth_header(world.account_a))

    assert response.status_code == 404


def test_another_firm_and_a_missing_one_answer_identically(client, world, auth_header):
    headers = auth_header(world.account_a)

    someone_elses = client.get(f"/firms/{world.firm_b}", headers=headers)
    nonexistent = client.get("/firms/999999", headers=headers)

    assert someone_elses.status_code == nonexistent.status_code == 404
    assert someone_elses.json() == nonexistent.json()


def test_leaving_the_roster_closes_the_door(client, db, world, auth_header):
    db.execute(
        text("UPDATE firm_member SET is_active = false WHERE firm_id = :f AND account_id = :a"),
        {"f": world.firm_a, "a": world.account_a},
    )

    response = client.get(f"/firms/{world.firm_a}", headers=auth_header(world.account_a))

    assert response.status_code == 404


def test_a_suspended_firm_locks_out_its_own_owner(client, db, world, auth_header):
    db.execute(text("UPDATE firm SET is_active = false WHERE id = :id"), {"id": world.firm_a})

    response = client.get(f"/firms/{world.firm_a}", headers=auth_header(world.account_a))

    assert response.status_code == 404


def test_anonymous_gets_401_before_any_404(client, world):
    """The frontend needs the 401 to send them to the login. It also means an
    anonymous caller learns nothing about which firms exist."""
    assert client.get(f"/firms/{world.firm_a}").status_code == 401


def test_a_non_numeric_firm_is_a_validation_error(client, world, auth_header):
    """Not a 500: the path parameter is typed."""
    response = client.get("/firms/abc", headers=auth_header(world.account_a))

    assert response.status_code == 422
