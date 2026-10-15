"""Pins the dashboard endpoint (HU-19): who reaches it, and that every number in it is
the number of the section it comes from.

The spread by month is pinned in test_projection.py, the progress in HU-16's tests
and the budget in HU-11's; here each block is checked against the endpoint of its
own section, which is the criterion "los números coinciden".

October 2026: the 26th is a Monday. Today is frozen on the 12th.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

TODAY = date(2026, 10, 12)
WALL = "Pared de ladrillo común 15cm"


def url(world, project_id: int | None = None, firm_id: int | None = None) -> str:
    firm = firm_id or world.firm_a
    return f"/firms/{firm}/projects/{project_id or world.project_a}"


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch) -> None:
    monkeypatch.setattr("app.services.tasks.today", lambda: TODAY)
    monkeypatch.setattr("app.api.routes.dashboard.today", lambda: TODAY)


@pytest.fixture
def team(world, new_member, add_project_member):
    collaborator = new_member(world.firm_a, "carlos@test.com", "architect")
    client = new_member(world.firm_a, "clara@test.com", "client")
    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, collaborator, world.firm_a, "collaborator")
    add_project_member(world.project_a, client, world.firm_a, "client")
    return {
        "lead": world.account_a2,
        "collaborator": collaborator,
        "client": client,
        "owner": world.account_a,
        "stranger": world.account_b,
    }


@pytest.fixture
def lead(team, auth_header) -> dict[str, str]:
    return auth_header(team["lead"])


@pytest.fixture
def planned_work(db, world, add_task, add_takeoff_line, recipe_id):
    """Work A starting Monday 26/10: a ten-day task with a wall assigned, which
    spans October and November, a one-day task after it, and a wall left out."""
    db.execute(
        text("UPDATE project SET estimated_start_date = '2026-10-26' WHERE id = :p"),
        {"p": world.project_a},
    )
    walls = add_task(world.project_a, world.firm_a, "Mampostería", duration=10)
    paint = add_task(world.project_a, world.firm_a, "Pintura", duration=1)
    db.execute(
        text(
            "INSERT INTO project_task_dependency (predecessor_id, successor_id, project_id)"
            " VALUES (:a, :b, :p)"
        ),
        {"a": walls, "b": paint, "p": world.project_a},
    )
    add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=walls)
    add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "70")


class TestAccess:
    @pytest.mark.parametrize("role", ["lead", "collaborator", "owner"])
    def test_whoever_sees_costs_reads_it(self, client, world, team, auth_header, role):
        response = client.get(f"{url(world)}/dashboard", headers=auth_header(team[role]))

        assert response.status_code == 200

    def test_the_client_of_the_work_does_not(self, client, world, team, auth_header):
        response = client.get(f"{url(world)}/dashboard", headers=auth_header(team["client"]))

        assert response.status_code == 403

    def test_another_firms_work_is_404(self, client, world, team, auth_header):
        """The URL names firm A; project B is not theirs to see, as in HU-11."""
        response = client.get(
            f"{url(world, world.project_b)}/dashboard", headers=auth_header(team["owner"])
        )

        assert response.status_code == 404

    def test_an_archived_work_is_a_404(self, db, client, world, team, lead):
        db.execute(
            text("UPDATE project SET is_active = false WHERE id = :p"), {"p": world.project_a}
        )

        assert client.get(f"{url(world)}/dashboard", headers=lead).status_code == 404


class TestBudget:
    def test_without_a_saved_budget_there_is_no_original(self, client, world, team, lead):
        budget = client.get(f"{url(world)}/dashboard", headers=lead).json()["budget"]

        assert budget["original"] is None
        assert budget["difference"] is None

    def test_the_original_is_v1_and_the_updated_is_the_budget_tab(
        self, client, world, team, lead, recipe_id, add_takeoff_line
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "100")
        client.post(f"{url(world)}/budget/versions", json={"note": "Presentado"}, headers=lead)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "50")
        client.post(f"{url(world)}/budget/versions", json={"note": "Ampliación"}, headers=lead)

        budget = client.get(f"{url(world)}/dashboard", headers=lead).json()["budget"]
        live = client.get(f"{url(world)}/budget", headers=lead).json()
        versions = client.get(f"{url(world)}/budget/versions", headers=lead).json()
        v1 = next(version for version in versions if version["version_number"] == 1)

        assert budget["original"]["version_number"] == 1
        assert budget["original"]["note"] == "Presentado"
        assert Decimal(budget["original"]["total"]) == Decimal(v1["total"])
        assert Decimal(budget["updated_total"]) == Decimal(live["total"])
        assert Decimal(budget["difference"]) == Decimal(live["total"]) - Decimal(v1["total"])
        # 150 m2 against 100 m2 of the same wall: half again.
        assert budget["difference_percent"] == "50.0"
        assert budget["direction"] == "above"


class TestProgressAndProjection:
    def test_the_progress_block_is_the_planning_tab(self, client, world, team, lead, planned_work):
        client.post(f"{url(world)}/tasks/baseline", headers=lead)

        dashboard = client.get(f"{url(world)}/dashboard", headers=lead).json()
        planning = client.get(f"{url(world)}/tasks", headers=lead).json()

        block = dashboard["progress"]
        assert block["progress"] == planning["progress"]
        assert block["planned_end_date"] == planning["planned_end_date"] == "2026-11-09"
        assert block["baseline_end_date"] == planning["baseline_end_date"]
        assert block["end_delay_days"] == 0
        assert block["overdue_tasks"] == 0

    def test_a_task_past_its_fixed_end_counts_as_overdue(
        self, db, client, world, team, lead, planned_work, monkeypatch
    ):
        client.post(f"{url(world)}/tasks/baseline", headers=lead)
        # Mampostería and Pintura were fixed to end on 6/11 and 9/11; on the
        # 10th neither is finished.
        later = date(2026, 11, 10)
        monkeypatch.setattr("app.services.tasks.today", lambda: later)
        monkeypatch.setattr("app.api.routes.dashboard.today", lambda: later)

        block = client.get(f"{url(world)}/dashboard", headers=lead).json()["progress"]

        assert block["overdue_tasks"] == 2

    def test_without_a_fixed_planning_there_is_no_comparison(
        self, client, world, team, lead, planned_work
    ):
        block = client.get(f"{url(world)}/dashboard", headers=lead).json()["progress"]

        assert block["progress"] is None
        assert block["end_delay_days"] is None
        assert block["has_tasks"] is True

    def test_the_projection_adds_up_to_the_planning_total(
        self, client, world, team, lead, planned_work
    ):
        projection = client.get(f"{url(world)}/dashboard", headers=lead).json()["projection"]
        planning = client.get(f"{url(world)}/tasks", headers=lead).json()

        assert [month["month"] for month in projection["months"]] == ["2026-10-01", "2026-11-01"]
        # Five working days in each month, so the wall is spent half and half.
        october, november = (Decimal(month["amount"]) for month in projection["months"])
        assert october == november
        assert projection["unassigned_cost"] == planning["unassigned_cost"]
        assert Decimal(projection["projected_total"]) + Decimal(
            projection["unassigned_cost"]
        ) == Decimal(planning["total_cost"])
        assert [month["is_past"] for month in projection["months"]] == [False, False]

    def test_without_a_start_date_there_is_nothing_to_project(
        self, client, world, team, lead, add_task
    ):
        add_task(world.project_a, world.firm_a, "Mampostería")

        projection = client.get(f"{url(world)}/dashboard", headers=lead).json()["projection"]

        assert projection["months"] == []
        assert projection["projected_total"] == "0.00"
