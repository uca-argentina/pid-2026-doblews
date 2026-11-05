"""Pins "Mis obras" (HU-26, ADR-013 section 3): which works come back, and that
every number on a card is the number of the section it comes from.

The progress and the dates are checked against the planning endpoint and the
latest version against the versions listing, which is what makes the cards
agree with the tabs they summarise.

October 2026: the 26th is a Monday. Today is frozen on the 12th.
"""

from datetime import date

import pytest
from sqlalchemy import text

TODAY = date(2026, 10, 12)
WALL = "Pared de ladrillo común 15cm"


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch) -> None:
    monkeypatch.setattr("app.services.tasks.today", lambda: TODAY)


@pytest.fixture
def team(world, new_member, add_project_member):
    """Work A: alba leads it and clara is its client. Work A2, of the same firm,
    has neither of them."""
    client_account = new_member(world.firm_a, "clara@test.com", "client")
    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, client_account, world.firm_a, "client")
    return {"lead": world.account_a2, "client": client_account, "owner": world.account_a}


@pytest.fixture
def other_work(world, new_project) -> int:
    return new_project(world.firm_a, world.account_a, "Casa Oeste")


@pytest.fixture
def planned_work(db, world, add_task, add_takeoff_line, recipe_id):
    """Work A starting Monday 26/10, with a ten-day task carrying a wall."""
    db.execute(
        text("UPDATE project SET estimated_start_date = '2026-10-26' WHERE id = :p"),
        {"p": world.project_a},
    )
    walls = add_task(world.project_a, world.firm_a, "Mampostería", duration=10)
    add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=walls)


def overview_url(world, firm_id: int | None = None) -> str:
    return f"/firms/{firm_id or world.firm_a}/projects/overview"


def work_url(world, path: str) -> str:
    return f"/firms/{world.firm_a}/projects/{world.project_a}/{path}"


def overview(client, world, headers) -> dict[int, dict]:
    response = client.get(overview_url(world), headers=headers)
    assert response.status_code == 200, response.text
    return {card["id"]: card for card in response.json()}


class TestWhichWorks:
    def test_the_client_sees_only_their_works(self, client, world, team, other_work, auth_header):
        cards = overview(client, world, auth_header(team["client"]))

        assert list(cards) == [world.project_a]
        assert cards[world.project_a]["name"] == "Casa Norte"
        assert cards[world.project_a]["client"]["name"] == "clara"

    def test_an_architect_sees_the_works_they_are_on(
        self, client, world, team, other_work, auth_header
    ):
        assert list(overview(client, world, auth_header(team["lead"]))) == [world.project_a]

    def test_the_owner_sees_every_work_of_the_firm(
        self, client, world, team, other_work, auth_header
    ):
        cards = overview(client, world, auth_header(team["owner"]))

        assert set(cards) == {world.project_a, other_work}

    def test_a_client_with_no_works_gets_an_empty_list(
        self, client, world, new_member, auth_header
    ):
        lonely = new_member(world.firm_a, "lucia@test.com", "client")

        assert overview(client, world, auth_header(lonely)) == {}

    def test_an_archived_work_is_left_out(self, db, client, world, team, auth_header):
        db.execute(
            text("UPDATE project SET is_active = false WHERE id = :p"), {"p": world.project_a}
        )

        assert overview(client, world, auth_header(team["client"])) == {}

    def test_another_firm_is_a_404(self, client, world, team, auth_header):
        response = client.get(
            overview_url(world, world.firm_b), headers=auth_header(team["client"])
        )

        assert response.status_code == 404

    def test_the_path_is_not_read_as_a_work_id(self, client, world, team, auth_header):
        """A literal segment ahead of /{project_id}: "overview" is not a bad id."""
        response = client.get(overview_url(world), headers=auth_header(team["owner"]))

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestProgressAndDates:
    def test_a_work_without_tasks_has_nothing_to_measure(self, client, world, team, auth_header):
        card = overview(client, world, auth_header(team["client"]))[world.project_a]

        assert card["has_tasks"] is False
        assert card["progress"] is None
        assert card["planned_end_date"] is None

    def test_before_the_planning_is_fixed_there_is_an_end_but_no_comparison(
        self, client, world, team, planned_work, auth_header
    ):
        card = overview(client, world, auth_header(team["client"]))[world.project_a]

        assert card["has_tasks"] is True
        assert card["progress"] is None
        assert card["baseline_end_date"] is None
        assert card["planned_end_date"] == "2026-11-06"

    def test_the_numbers_are_the_planning_tabs(
        self, client, world, team, planned_work, auth_header
    ):
        lead = auth_header(team["lead"])
        client.post(work_url(world, "tasks/baseline"), headers=lead)
        planning = client.get(work_url(world, "tasks"), headers=lead).json()

        card = overview(client, world, auth_header(team["client"]))[world.project_a]

        assert card["progress"] == planning["progress"]
        assert card["progress"] is not None
        assert card["planned_end_date"] == planning["planned_end_date"]
        assert card["baseline_end_date"] == planning["baseline_end_date"]
        assert card["project_start_date"] == planning["project_start_date"] == "2026-10-26"


class TestLatestVersion:
    def test_none_while_nothing_was_saved(self, client, world, team, auth_header):
        card = overview(client, world, auth_header(team["client"]))[world.project_a]

        assert card["latest_version"] is None

    def test_the_highest_version_as_the_listing_shows_it(
        self, client, world, team, recipe_id, add_takeoff_line, auth_header
    ):
        lead = auth_header(team["lead"])
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        client.post(work_url(world, "budget/versions"), json={"note": "Presentado"}, headers=lead)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "30")
        client.post(work_url(world, "budget/versions"), json={"note": "Ampliación"}, headers=lead)
        newest = client.get(work_url(world, "budget/versions"), headers=lead).json()[0]

        latest = overview(client, world, auth_header(team["client"]))[world.project_a][
            "latest_version"
        ]

        assert latest["version_number"] == 2
        assert {key: latest[key] for key in ("id", "total", "currency", "created_at")} == {
            key: newest[key] for key in ("id", "total", "currency", "created_at")
        }

    def test_the_owner_reads_it_through_view_all(
        self, client, world, team, recipe_id, add_takeoff_line, auth_header
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        client.post(work_url(world, "budget/versions"), json={}, headers=auth_header(team["lead"]))

        card = overview(client, world, auth_header(team["owner"]))[world.project_a]

        assert card["latest_version"]["version_number"] == 1

    def test_it_stays_empty_for_whoever_may_not_read_versions(
        self, db, client, world, team, recipe_id, add_takeoff_line, auth_header
    ):
        """No role on a work lacks the permission today (ADR-013 section 1), so
        the client's role loses it here to prove the rule is asked per work."""
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")
        client.post(work_url(world, "budget/versions"), json={}, headers=auth_header(team["lead"]))
        db.execute(
            text(
                "DELETE FROM role_permission WHERE role_id ="
                " (SELECT id FROM role WHERE code = 'client' AND scope = 'project')"
                " AND permission_id ="
                " (SELECT id FROM permission WHERE code = 'project.budget_version.view')"
            )
        )

        card = overview(client, world, auth_header(team["client"]))[world.project_a]

        assert card["latest_version"] is None
