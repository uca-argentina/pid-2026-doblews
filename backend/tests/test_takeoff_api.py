"""Pins the take-off endpoints at the border: who gets which status code, and who sees costs.
The rules and the numbers are pinned in the service and repository tests; here it is
the permissions of ADR-003 section 8 and the 404s that keep other works invisible.
"""

import pytest
from sqlalchemy import text

from app.services.takeoff import RECIPE_NOT_AVAILABLE

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"


def takeoff_url(world, project_id: int | None = None, line_id: int | None = None) -> str:
    base = f"/firms/{world.firm_a}/projects/{project_id or world.project_a}/takeoff"
    return base if line_id is None else f"{base}/lines/{line_id}"


def lines_url(world, project_id: int | None = None) -> str:
    return f"{takeoff_url(world, project_id)}/lines"


def archive(db, project_id: int) -> None:
    """Archive a work behind the API's back, as HU-3's DELETE does."""
    db.execute(text("UPDATE project SET is_active = false WHERE id = :p"), {"p": project_id})


@pytest.fixture
def team(world, new_member, add_project_member):
    """One person per project role on work A, plus the people who are not on it.

    Alba, an architect of the firm, leads it. Ana owns the firm and is on no
    work: she reaches the take-off only through project.view_all.
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
    """120 m2 of wall on work A: the example of ADR-003."""
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", note="PB")


class TestRead:
    def test_the_lead_reads_lines_materials_and_costs(
        self, client, world, team, wall, recipe_id, auth_header
    ):
        response = client.get(takeoff_url(world), headers=auth_header(team["lead"]))

        assert response.status_code == 200
        body = response.json()

        (line,) = body["lines"]
        assert line["id"] == wall
        assert (line["recipe"]["id"], line["recipe"]["name"]) == (recipe_id[WALL], WALL)
        assert line["recipe"]["unit"]["code"] == "m2"
        assert (line["quantity"], line["note"]) == ("120.000", "PB")

        brick = next(material for material in body["materials"] if material["name"] == BRICK)
        # Decimals travel as strings, so the frontend never sees a float.
        assert (brick["quantity"], brick["cost"], brick["currency"]) == (
            "7200.000",
            "1656000.00",
            "ARS",
        )

        # 2,665,800 of materials plus T-06's hours: 120 h of Oficial and of Ayudante.
        assert body["total_cost"] == "3877800.00"
        assert body["currency"] == "ARS"
        assert body["prices_as_of"] is not None

    @pytest.mark.parametrize("role", ["collaborator", "viewer", "owner"])
    def test_these_roles_see_the_costs(self, client, world, team, wall, auth_header, role):
        """viewer holds project.cost.view; the owner sees them through project.view_all."""
        body = client.get(takeoff_url(world), headers=auth_header(team[role])).json()

        assert body["total_cost"] == "3877800.00"
        assert all(material["cost"] is not None for material in body["materials"])

    def test_the_client_sees_quantities_and_no_costs(self, client, world, team, wall, auth_header):
        """ADR-003 section 8: the client sees what their work needs, not what it
        costs the firm."""
        response = client.get(takeoff_url(world), headers=auth_header(team["client"]))

        assert response.status_code == 200
        body = response.json()
        assert body["total_cost"] is None
        assert all(material["cost"] is None for material in body["materials"])
        assert {material["name"]: material["quantity"] for material in body["materials"]}[
            BRICK
        ] == "7200.000"

    def test_an_empty_take_off_costs_zero(self, client, world, team, auth_header):
        body = client.get(takeoff_url(world), headers=auth_header(team["lead"])).json()

        assert body == {
            "lines": [],
            "materials": [],
            "total_cost": "0.00",
            "currency": "ARS",
            "prices_as_of": None,
        }

    @pytest.mark.parametrize("role", ["bystander", "stranger"])
    def test_someone_off_the_work_gets_404(self, client, world, team, wall, auth_header, role):
        """An architect of the firm who is not on the work, and someone of another
        firm: neither may learn the work exists."""
        response = client.get(takeoff_url(world), headers=auth_header(team[role]))

        assert response.status_code == 404

    def test_an_archived_work_is_404(self, client, db, world, team, wall, auth_header):
        archive(db, world.project_a)

        response = client.get(takeoff_url(world), headers=auth_header(team["lead"]))

        assert response.status_code == 404


class TestCreate:
    @pytest.mark.parametrize("role", ["lead", "collaborator"])
    def test_those_who_manage_load_a_line(self, client, world, team, recipe_id, auth_header, role):
        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "12.5", "note": "  sector A  "},
            headers=auth_header(team[role]),
        )

        assert response.status_code == 201
        body = response.json()
        assert (body["recipe"]["name"], body["quantity"], body["note"]) == (
            WALL,
            "12.500",
            "sector A",
        )

    def test_the_new_line_shows_up_in_the_take_off(
        self, client, world, team, recipe_id, auth_header
    ):
        headers = auth_header(team["lead"])
        client.post(
            lines_url(world), json={"recipe_id": recipe_id[WALL], "quantity": "1"}, headers=headers
        )

        body = client.get(takeoff_url(world), headers=headers).json()

        assert len(body["lines"]) == 1
        assert body["total_cost"] != "0.00"

    def test_a_blank_note_is_stored_as_none(self, client, world, team, recipe_id, auth_header):
        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "1", "note": "   "},
            headers=auth_header(team["lead"]),
        )

        assert response.json()["note"] is None

    @pytest.mark.parametrize("quantity", ["0", "-5", "1.2345", "abc"])
    def test_a_bad_quantity_is_422(self, client, world, team, recipe_id, auth_header, quantity):
        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": quantity},
            headers=auth_header(team["lead"]),
        )

        assert response.status_code == 422

    def test_a_retired_recipe_is_409(self, client, db, world, team, recipe_id, auth_header):
        db.execute(
            text("UPDATE recipe SET is_active = false WHERE id = :r"), {"r": recipe_id[WALL]}
        )

        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "1"},
            headers=auth_header(team["lead"]),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == RECIPE_NOT_AVAILABLE

    def test_another_firm_s_recipe_is_the_same_409(
        self, client, world, team, auth_header, add_firm_recipe
    ):
        """Same status and body as a retired recipe (ADR-006 rule 1)."""
        theirs = add_firm_recipe(world.firm_b)

        response = client.post(
            lines_url(world),
            json={"recipe_id": theirs, "quantity": "1"},
            headers=auth_header(team["lead"]),
        )

        assert response.status_code == 409
        assert response.json()["detail"] == RECIPE_NOT_AVAILABLE

    @pytest.mark.parametrize("role", ["viewer", "client", "owner"])
    def test_those_who_only_read_get_403(self, client, world, team, recipe_id, auth_header, role):
        """They can already see the work, so hiding it protects nothing: 403, not 404.
        The owner included — project.view_all opens the reading, not the writing."""
        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "1"},
            headers=auth_header(team[role]),
        )

        assert response.status_code == 403

    @pytest.mark.parametrize("role", ["bystander", "stranger"])
    def test_someone_off_the_work_gets_404(self, client, world, team, recipe_id, auth_header, role):
        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "1"},
            headers=auth_header(team[role]),
        )

        assert response.status_code == 404

    def test_an_archived_work_is_404(self, client, db, world, team, recipe_id, auth_header):
        archive(db, world.project_a)

        response = client.post(
            lines_url(world),
            json={"recipe_id": recipe_id[WALL], "quantity": "1"},
            headers=auth_header(team["lead"]),
        )

        assert response.status_code == 404


class TestUpdate:
    def test_the_quantity_and_note_are_replaced(self, client, world, team, wall, auth_header):
        response = client.put(
            takeoff_url(world, line_id=wall),
            json={"quantity": "80"},
            headers=auth_header(team["collaborator"]),
        )

        assert response.status_code == 200
        body = response.json()
        # No note sent: the PUT clears the "PB" it had.
        assert (body["id"], body["quantity"], body["note"]) == (wall, "80.000", None)

    def test_the_recipe_in_the_body_is_ignored(
        self, client, world, team, wall, recipe_id, auth_header
    ):
        other = recipe_id["Carpeta de cemento"]

        body = client.put(
            takeoff_url(world, line_id=wall),
            json={"quantity": "80", "recipe_id": other},
            headers=auth_header(team["lead"]),
        ).json()

        assert body["recipe"]["name"] == WALL

    def test_a_line_of_another_work_is_404(
        self, client, world, team, recipe_id, add_takeoff_line, new_project, auth_header
    ):
        """Work A's URL, a line of work B of the same firm."""
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        line = add_takeoff_line(other, world.firm_a, recipe_id[WALL], "10")

        response = client.put(
            takeoff_url(world, line_id=line),
            json={"quantity": "80"},
            headers=auth_header(team["lead"]),
        )

        assert response.status_code == 404

    def test_the_viewer_gets_403(self, client, world, team, wall, auth_header):
        response = client.put(
            takeoff_url(world, line_id=wall),
            json={"quantity": "80"},
            headers=auth_header(team["viewer"]),
        )

        assert response.status_code == 403


class TestDelete:
    def test_the_line_leaves_the_take_off(self, client, world, team, wall, auth_header):
        headers = auth_header(team["lead"])

        response = client.delete(takeoff_url(world, line_id=wall), headers=headers)

        assert response.status_code == 204
        body = client.get(takeoff_url(world), headers=headers).json()
        assert (body["lines"], body["materials"], body["total_cost"]) == ([], [], "0.00")

    def test_the_row_stays_in_the_database(self, client, db, world, team, wall, auth_header):
        client.delete(takeoff_url(world, line_id=wall), headers=auth_header(team["lead"]))

        is_active = db.execute(
            text("SELECT is_active FROM project_recipe WHERE id = :l"), {"l": wall}
        ).scalar_one()
        assert is_active is False

    def test_a_removed_line_cannot_be_removed_again(self, client, world, team, wall, auth_header):
        headers = auth_header(team["lead"])
        client.delete(takeoff_url(world, line_id=wall), headers=headers)

        response = client.delete(takeoff_url(world, line_id=wall), headers=headers)

        assert response.status_code == 404

    def test_the_client_gets_403(self, client, world, team, wall, auth_header):
        response = client.delete(
            takeoff_url(world, line_id=wall), headers=auth_header(team["client"])
        )

        assert response.status_code == 403
