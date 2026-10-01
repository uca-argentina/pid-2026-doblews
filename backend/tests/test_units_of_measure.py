"""GET /units-of-measure: the platform's catalogue, per HU-0.

Two things are being proved here. That the seed migration loaded exactly the
seven units HU-0 lists plus the hour T-06 adds — typed out by hand, for the same reason as
test_rbac_catalog_seed.py: a check that reads the seed's own source only
proves the source equals itself. And that the endpoint demands a session but
nothing else, since the catalogue is global and holds no firm's data.
"""

from sqlalchemy import Connection, text

# (code, magnitude), from HU-0's acceptance criteria, plus T-06's hour. name/abbreviation are
# exercised through the endpoint response below instead of duplicated here.
EXPECTED_UNITS: dict[str, str] = {
    "m2": "superficie",
    "m3": "volumen",
    "ml": "longitud",
    "u": "cantidad",
    "kg": "peso",
    "bolsa": "cantidad",
    "lt": "volumen",
    "h": "tiempo",
}


def units_of_measure(client, headers=None):
    return client.get("/units-of-measure", headers=headers or {})


def test_the_catalogue_holds_exactly_the_seeded_units(db: Connection) -> None:
    rows = db.execute(text("SELECT code, magnitude FROM unit_of_measure")).all()
    assert {row.code: row.magnitude for row in rows} == EXPECTED_UNITS


def test_without_a_token_it_refuses(client):
    response = units_of_measure(client)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_any_active_account_reads_the_whole_catalogue(client, world, auth_header):
    """Global to the platform (ADR-003 section 7): no firm/project scoping, so
    an ordinary firm member — not just an owner — sees every row."""
    response = units_of_measure(client, auth_header(world.account_a))

    assert response.status_code == 200
    body = response.json()
    assert {row["code"] for row in body} == set(EXPECTED_UNITS)


def test_returns_the_shape_the_frontend_select_needs_in_code_order(client, world, auth_header):
    body = units_of_measure(client, auth_header(world.account_a)).json()

    assert [row["code"] for row in body] == sorted(EXPECTED_UNITS)
    assert body[4] == {
        "id": body[4]["id"],
        "code": "m2",
        "name": "Metro cuadrado",
        "abbreviation": "m2",
        "magnitude": "superficie",
    }
