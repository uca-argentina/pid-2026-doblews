"""What the client of a work reaches, and what stays shut (HU-25, ADR-013).

The table of ADR-013 section 2, turned into status codes. It is one file and
not a line added to each feature's tests on purpose: the rule it defends — "el
cliente ve su obra y no ve los costos internos del estudio", with exactly one
exception — is about the set of doors taken together, and a list of them in one
place is what a reviewer can read against the ADR.

The permissions themselves are pinned in test_rbac_catalog_seed.py. Here it is
the border: the same client, asking for everything.
"""

from decimal import Decimal

import pytest

WALL = "Pared de ladrillo común 15cm"


@pytest.fixture
def team(world, new_member, add_project_member):
    """The lead who builds the work, and the client who only reads it."""
    client_account = new_member(world.firm_a, "clara@test.com", "client")
    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, client_account, world.firm_a, "client")
    return {"lead": world.account_a2, "client": client_account, "owner": world.account_a}


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")


@pytest.fixture
def as_client(team, auth_header) -> dict[str, str]:
    return auth_header(team["client"])


def project_url(world, path: str = "") -> str:
    base = f"/firms/{world.firm_a}/projects/{world.project_a}"
    return f"{base}/{path}" if path else base


# --- what the client reads ----------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "",  # the work itself
        "takeoff",  # the quantities, with no money on them
        "tasks",  # the planning, which is also the Gantt and the progress
        "budget/versions",  # new in HU-25
    ],
)
def test_the_client_reads_these(client, world, team, wall, as_client, path):
    """ADR-013 section 2. The first three were already theirs; the fourth is
    what this story adds."""
    assert client.get(project_url(world, path), headers=as_client).status_code == 200


def test_the_client_sees_the_quantities_without_their_cost(client, world, team, wall, as_client):
    """Not a door but the shape behind one: the take-off opens for them and
    answers with the money emptied out (ADR-003 section 8, still standing).

    The fields are there and null rather than absent, which is the shape the
    screen was built to read.
    """
    body = client.get(project_url(world, "takeoff"), headers=as_client).json()

    assert body["materials"], "the take-off has something to look at"
    assert body["total_cost"] is None
    assert all(material["cost"] is None for material in body["materials"])
    assert all(Decimal(material["quantity"]) > 0 for material in body["materials"])


# --- what stays shut ----------------------------------------------------------


@pytest.mark.parametrize(
    ("what", "path"),
    [
        ("el presupuesto vivo", "budget"),
        ("el dashboard", "dashboard"),
        ("la comparación de compras", "purchasing"),
        ("las órdenes de la obra", "purchase-orders"),
    ],
)
def test_the_client_is_refused_these_of_the_work(client, world, team, wall, as_client, what, path):
    """ADR-013 section 4, rule 2. 403 and not 404: they may see the work, so
    pretending it does not exist would be a lie they can disprove."""
    response = client.get(project_url(world, path), headers=as_client)

    assert response.status_code == 403, f"{what} abierto para el cliente"


@pytest.mark.parametrize(
    ("what", "path"),
    [
        ("los proveedores", "suppliers"),
        ("las órdenes del estudio", "purchase-orders"),
        ("el nivel del estudio", "loyalty"),
    ],
)
def test_the_client_is_refused_these_of_the_firm(client, world, as_client, what, path):
    """The firm's own sections. The client holds firm.view and catalog.view and
    nothing else (ADR-010 section 6, ADR-011 section 6, ADR-012 section 6)."""
    response = client.get(f"/firms/{world.firm_a}/{path}", headers=as_client)

    assert response.status_code == 403, f"{what} abierto para el cliente"


def test_the_client_does_not_change_the_planning(client, world, team, wall, as_client):
    """Every control the planning screen draws is behind project.task.manage,
    and so is the route under it: reading the tasks is not writing them."""
    response = client.post(
        project_url(world, "tasks"),
        json={"name": "Una tarea del cliente", "estimated_duration_days": 3},
        headers=as_client,
    )

    assert response.status_code == 403


# --- and only their own works -------------------------------------------------


def test_a_client_does_not_reach_a_work_they_are_not_on(
    client, world, team, as_client, new_project
):
    """ADR-013 section 4, rule 3. Another work of the same firm, which they are
    not a member of: 404, because it is none of theirs to know about."""
    other = new_project(world.firm_a, world.account_a, "Casa Ajena")

    listing = client.get(
        f"/firms/{world.firm_a}/projects/{other}/budget/versions", headers=as_client
    )

    assert listing.status_code == 404


def test_the_lead_and_the_owner_keep_what_they_had(client, world, team, wall, auth_header):
    """ADR-013 section 4, rule 4. The permission moved under them; nothing of
    what they reach moved with it."""
    for role in ("lead", "owner"):
        headers = auth_header(team[role])
        for path in ("budget", "budget/versions", "dashboard", "purchasing"):
            response = client.get(project_url(world, path), headers=headers)
            assert response.status_code == 200, f"{role} perdió {path}"
