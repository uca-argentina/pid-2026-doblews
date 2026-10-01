"""Pins the budget endpoint of HU-11: who may read it, and that what it shows adds up.

The grouping and the arithmetic are the point here — the repository tests already
pin the quantities — together with the one rule that makes this its own endpoint:
the client of the work reads the take-off and does not read this.
"""

import pytest
from sqlalchemy import text

WALL = "Pared de ladrillo común 15cm"
SUBFLOOR = "Contrapiso de cascote"


def budget_url(world, project_id: int | None = None) -> str:
    return f"/firms/{world.firm_a}/projects/{project_id or world.project_a}/budget"


def archive(db, project_id: int) -> None:
    """Archive a work behind the API's back, as HU-3's DELETE does."""
    db.execute(text("UPDATE project SET is_active = false WHERE id = :p"), {"p": project_id})


def group(body, type_: str) -> dict:
    return next(found for found in body["groups"] if found["type"] == type_)


def amounts(group_body) -> dict[str, str]:
    """resource name -> subtotal, which is what most assertions compare."""
    return {item["name"]: item["subtotal"] for item in group_body["items"]}


@pytest.fixture
def team(world, new_member, add_project_member):
    """One person per project role on work A, plus the people who are not on it.

    The same cast as the take-off's tests, so the two endpoints are compared on
    the same people: what changes between them is the guard, not the roster.
    """
    collaborator = new_member(world.firm_a, "carlos@test.com", "architect")
    viewer = new_member(world.firm_a, "vera@test.com", "architect")
    client = new_member(world.firm_a, "clara@test.com", "client")
    bystander = new_member(world.firm_a, "otto@test.com", "architect")

    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, collaborator, world.firm_a, "collaborator")
    add_project_member(world.project_a, viewer, world.firm_a, "viewer")
    add_project_member(world.project_a, client, world.firm_a, "client")

    return {
        "lead": world.account_a2,
        "collaborator": collaborator,
        "viewer": viewer,
        "client": client,
        "owner": world.account_a,
        "bystander": bystander,
        "stranger": world.account_b,
    }


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    """120 m2 of wall on work A: the example of ADR-003, now with its hours."""
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")


class TestRead:
    def test_the_wall_is_split_into_materials_and_labour(
        self, client, world, team, wall, auth_header
    ):
        """120 m2 of wall: four materials, two trades, and no equipment."""
        response = client.get(budget_url(world), headers=auth_header(team["lead"]))

        assert response.status_code == 200
        body = response.json()

        assert [found["type"] for found in body["groups"]] == ["material", "labor", "equipment"]
        assert amounts(group(body, "material")) == {
            "Arena gruesa": "253800.00",
            "Cal hidratada (bolsa 25 kg)": "276000.00",
            "Cemento portland (bolsa 50 kg)": "480000.00",
            "Ladrillo común": "1656000.00",
        }
        assert amounts(group(body, "labor")) == {
            "Ayudante": "552000.00",
            "Oficial": "660000.00",
        }
        assert group(body, "equipment")["items"] == []

    def test_every_subtotal_adds_up_to_the_total(self, client, world, team, wall, auth_header):
        """The promise of HU-11: the screen adds up, down to the cent."""
        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        for found in body["groups"]:
            assert sum(float(item["subtotal"]) for item in found["items"]) == float(
                found["subtotal"]
            )

        assert (group(body, "material")["subtotal"], group(body, "labor")["subtotal"]) == (
            "2665800.00",
            "1212000.00",
        )
        assert group(body, "equipment")["subtotal"] == "0.00"
        # The same total the take-off of HU-5 reports, since it is the same rows.
        assert body["total"] == "3877800.00"
        assert body["currency"] == "ARS"

    def test_an_item_carries_its_unit_and_reference_price(
        self, client, world, team, wall, auth_header
    ):
        """An hour of labour is priced per hour (T-06), which is what makes the
        'precio unitario' column mean the same thing in the three groups."""
        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        oficial = next(item for item in group(body, "labor")["items"] if item["name"] == "Oficial")

        assert oficial["unit"]["code"] == "h"
        assert (oficial["quantity"], oficial["unit_price"]) == ("120.000", "5500.00")

    def test_the_equipment_of_the_subfloor_lands_in_its_own_group(
        self, client, world, team, recipe_id, add_takeoff_line, auth_header
    ):
        """50 m3 of subfloor take 0.1 h of concrete mixer each: 5 h at 3,000."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[SUBFLOOR], "50")

        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        (mixer,) = group(body, "equipment")["items"]
        assert (mixer["name"], mixer["quantity"], mixer["unit_price"]) == (
            "Hormigonera",
            "5.000",
            "3000.00",
        )
        assert (mixer["subtotal"], group(body, "equipment")["subtotal"]) == (
            "15000.00",
            "15000.00",
        )

    def test_the_budget_says_when_its_prices_are_from(self, client, world, team, wall, auth_header):
        """ADR-005 section 5: the screen prints "precios de referencia al <fecha>"."""
        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        assert body["prices_as_of"] is not None

    def test_a_work_with_no_lines_is_three_empty_groups(self, client, world, team, auth_header):
        """The empty state: the shape is the same, so the screen asks one question."""
        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        assert body == {
            "groups": [
                {"type": "material", "items": [], "subtotal": "0.00"},
                {"type": "labor", "items": [], "subtotal": "0.00"},
                {"type": "equipment", "items": [], "subtotal": "0.00"},
            ],
            "total": "0.00",
            "currency": "ARS",
            "prices_as_of": None,
        }

    def test_removing_a_line_recalculates_the_budget(self, client, world, team, wall, auth_header):
        """It is the draft: no save step stands between the take-off and this."""
        client.delete(
            f"/firms/{world.firm_a}/projects/{world.project_a}/takeoff/lines/{wall}",
            headers=auth_header(team["lead"]),
        )

        body = client.get(budget_url(world), headers=auth_header(team["lead"])).json()

        assert body["total"] == "0.00"


class TestWhoMayRead:
    @pytest.mark.parametrize("role", ["lead", "collaborator", "viewer", "owner"])
    def test_these_roles_read_the_budget(self, client, world, team, wall, auth_header, role):
        """viewer holds project.cost.view; the owner comes in through project.view_all."""
        response = client.get(budget_url(world), headers=auth_header(team[role]))

        assert response.status_code == 200
        assert response.json()["total"] == "3877800.00"

    def test_the_client_does_not_see_the_section(self, client, world, team, wall, auth_header):
        """HU-11: the client reads the take-off with its costs emptied, and this
        not at all. 403 and not 404, because they may see the work itself."""
        response = client.get(budget_url(world), headers=auth_header(team["client"]))

        assert response.status_code == 403

    @pytest.mark.parametrize("role", ["bystander", "stranger"])
    def test_someone_off_the_work_gets_404(self, client, world, team, wall, auth_header, role):
        """An architect of the firm who is not on the work, and someone of another
        firm: neither may learn the work exists."""
        response = client.get(budget_url(world), headers=auth_header(team[role]))

        assert response.status_code == 404

    def test_an_archived_work_is_404(self, client, db, world, team, wall, auth_header):
        archive(db, world.project_a)

        response = client.get(budget_url(world), headers=auth_header(team["lead"]))

        assert response.status_code == 404

    def test_another_firms_work_is_404(self, client, world, team, auth_header):
        """The URL names firm A; project B is not theirs to price."""
        response = client.get(
            budget_url(world, world.project_b), headers=auth_header(team["owner"])
        )

        assert response.status_code == 404
