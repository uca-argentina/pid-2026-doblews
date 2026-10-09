"""Pins the planning endpoints at the border: who gets which status code, and who sees costs.
The rules are pinned in the service tests and the numbers in the repository's; here it
is the permissions of ADR-009 section 9, the 404s that keep other works invisible, and
that each rule reaches the caller as a 409 carrying its own sentence.
"""

import pytest
from sqlalchemy import text

from app.services.tasks import (
    ASSIGNEE_NOT_ALLOWED,
    DATE_NOT_EXPECTED,
    END_BEFORE_START,
    LINE_NOT_AVAILABLE,
    NAME_TAKEN,
    TASK_NOT_AVAILABLE,
    invalid_transition,
)

WALL = "Pared de ladrillo común 15cm"
# 120 m2 of the seeded wall, the example of ADR-003.
WALL_120 = "3877800.00"

WRITERS = ["lead", "collaborator"]
NOT_WRITERS = ["viewer", "client", "owner"]


def tasks_url(world, project_id: int | None = None, task_id: int | None = None) -> str:
    base = f"/firms/{world.firm_a}/projects/{project_id or world.project_a}/tasks"
    return base if task_id is None else f"{base}/{task_id}"


def line_task_url(world, line_id: int) -> str:
    return f"/firms/{world.firm_a}/projects/{world.project_a}/takeoff/lines/{line_id}/task"


def body(**overrides) -> dict:
    """A valid task form, with whatever a test wants to change."""
    return {"name": "Mampostería", "estimated_duration_days": 10, **overrides}


def archive(db, project_id: int) -> None:
    """Archive a work behind the API's back, as HU-3's DELETE does."""
    db.execute(text("UPDATE project SET is_active = false WHERE id = :p"), {"p": project_id})


@pytest.fixture
def team(world, new_member, add_project_member):
    """One person per project role on work A, plus the people who are not on it.

    Alba, an architect of the firm, leads it. Ana owns the firm and is on no
    work: she reaches the planning only through project.view_all.
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
def lead(team, auth_header) -> dict[str, str]:
    """The headers of the person who may do everything here."""
    return auth_header(team["lead"])


@pytest.fixture
def task(world, add_task) -> int:
    return add_task(world.project_a, world.firm_a, "Mampostería", duration=10)


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    """120 m2 of wall on work A, assigned to no task."""
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")


class TestRead:
    def test_the_lead_reads_the_tasks_and_what_they_cost(
        self, client, world, team, lead, task, recipe_id, add_takeoff_line
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")

        response = client.get(tasks_url(world), headers=lead)

        assert response.status_code == 200
        assert response.json() == {
            "tasks": [
                {
                    "id": task,
                    "name": "Mampostería",
                    "description": None,
                    "estimated_duration_days": 10,
                    "not_before_date": None,
                    "status": "pending",
                    "assignee": None,
                    "actual_start_date": None,
                    "actual_end_date": None,
                    # Decimals travel as strings, so the frontend never sees a float.
                    "cost": WALL_120,
                }
            ],
            "unassigned_cost": WALL_120,
            "total_cost": "7755600.00",
            "currency": "ARS",
        }

    def test_a_task_with_no_lines_costs_zero(self, client, world, team, lead, task):
        planning = client.get(tasks_url(world), headers=lead).json()

        assert planning["tasks"][0]["cost"] == "0.00"
        assert (planning["unassigned_cost"], planning["total_cost"]) == ("0.00", "0.00")

    def test_a_work_with_no_tasks_shows_its_whole_take_off_as_unassigned(
        self, client, world, team, lead, wall
    ):
        """The empty state of HU-13, with the amount still waiting to be planned."""
        planning = client.get(tasks_url(world), headers=lead).json()

        assert planning["tasks"] == []
        assert (planning["unassigned_cost"], planning["total_cost"]) == (WALL_120, WALL_120)

    def test_a_task_carries_its_assignee_by_name(self, client, world, team, lead, add_task):
        add_task(world.project_a, world.firm_a, assignee=team["collaborator"])

        (listed,) = client.get(tasks_url(world), headers=lead).json()["tasks"]

        assert listed["assignee"] == {"account_id": team["collaborator"], "name": "carlos"}

    @pytest.mark.parametrize("role", ["collaborator", "viewer", "owner"])
    def test_these_roles_see_the_costs(self, client, world, team, task, wall, auth_header, role):
        """viewer holds project.cost.view; the owner sees them through project.view_all."""
        planning = client.get(tasks_url(world), headers=auth_header(team[role])).json()

        assert planning["total_cost"] == WALL_120
        assert planning["tasks"][0]["cost"] == "0.00"

    def test_the_client_sees_the_tasks_and_no_costs(
        self, client, world, team, task, wall, auth_header
    ):
        """ADR-009 section 9: the client sees what is planned on their work, not
        what it costs the firm."""
        response = client.get(tasks_url(world), headers=auth_header(team["client"]))

        assert response.status_code == 200
        planning = response.json()
        assert [listed["name"] for listed in planning["tasks"]] == ["Mampostería"]
        assert planning["tasks"][0]["cost"] is None
        assert (planning["unassigned_cost"], planning["total_cost"]) == (None, None)

    def test_someone_of_the_firm_who_is_not_on_the_work_gets_404(
        self, client, world, team, auth_header
    ):
        response = client.get(tasks_url(world), headers=auth_header(team["bystander"]))

        assert response.status_code == 404

    def test_another_firms_work_is_a_404(self, client, world, team, lead):
        response = client.get(tasks_url(world, world.project_b), headers=lead)

        assert response.status_code == 404

    @pytest.mark.parametrize("role", ["lead", "owner"])
    def test_an_archived_work_is_a_404(self, db, client, world, team, auth_header, role):
        archive(db, world.project_a)

        response = client.get(tasks_url(world), headers=auth_header(team[role]))

        assert response.status_code == 404

    def test_without_a_token_it_is_a_401(self, client, world):
        assert client.get(tasks_url(world)).status_code == 401


class TestAssignees:
    def test_offers_whoever_may_manage_the_planning(self, client, world, team, lead):
        response = client.get(f"{tasks_url(world)}/assignees", headers=lead)

        assert response.status_code == 200
        assert response.json() == [
            {"account_id": team["lead"], "name": "alba"},
            {"account_id": team["collaborator"], "name": "carlos"},
        ]

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_is_closed_to_whoever_cannot_assign(self, client, world, team, auth_header, role):
        response = client.get(f"{tasks_url(world)}/assignees", headers=auth_header(team[role]))

        assert response.status_code == 403


class TestCreate:
    @pytest.mark.parametrize("role", WRITERS)
    def test_these_roles_load_a_task(self, client, world, team, auth_header, role):
        response = client.post(
            tasks_url(world),
            json=body(
                description="  Con ladrillo común  ",
                not_before_date="2026-11-02",
                assignee_account_id=team["collaborator"],
            ),
            headers=auth_header(team[role]),
        )

        assert response.status_code == 201
        created = response.json()
        assert created["id"] is not None
        assert (created["name"], created["status"]) == ("Mampostería", "pending")
        assert created["description"] == "Con ladrillo común"
        assert created["not_before_date"] == "2026-11-02"
        assert created["assignee"] == {"account_id": team["collaborator"], "name": "carlos"}
        assert (created["actual_start_date"], created["actual_end_date"]) == (None, None)
        assert created["cost"] == "0.00"

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403_and_nothing_is_written(
        self, db, client, world, team, auth_header, role
    ):
        """The owner included: project.view_all opens the reading, never the writing."""
        response = client.post(tasks_url(world), json=body(), headers=auth_header(team[role]))

        assert response.status_code == 403
        assert db.execute(text("SELECT count(*) FROM project_task")).scalar_one() == 0

    def test_a_name_already_in_use_is_a_409(self, client, world, team, lead, task):
        response = client.post(tasks_url(world), json=body(name="mampostería"), headers=lead)

        assert response.status_code == 409
        assert response.json()["detail"] == NAME_TAKEN

    def test_an_assignee_who_cannot_manage_the_planning_is_a_409(self, client, world, team, lead):
        response = client.post(
            tasks_url(world), json=body(assignee_account_id=team["viewer"]), headers=lead
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ASSIGNEE_NOT_ALLOWED

    def test_an_assignee_of_another_firm_is_the_same_409_and_not_a_500(
        self, client, world, team, lead
    ):
        response = client.post(
            tasks_url(world), json=body(assignee_account_id=team["stranger"]), headers=lead
        )

        assert response.status_code == 409
        assert response.json()["detail"] == ASSIGNEE_NOT_ALLOWED

    @pytest.mark.parametrize(
        "bad",
        [
            {"name": "   "},
            {"name": "x" * 151},
            {"estimated_duration_days": 0},
            {"estimated_duration_days": 2.5},
            {"not_before_date": "pronto"},
        ],
    )
    def test_a_malformed_body_is_a_422(self, client, world, team, lead, bad):
        response = client.post(tasks_url(world), json=body(**bad), headers=lead)

        assert response.status_code == 422

    def test_another_firms_work_is_a_404(self, client, world, team, lead):
        response = client.post(tasks_url(world, world.project_b), json=body(), headers=lead)

        assert response.status_code == 404


class TestUpdate:
    def test_the_form_replaces_every_field(self, client, world, team, lead, task):
        response = client.put(
            tasks_url(world, task_id=task),
            json=body(name="Mampostería PB", estimated_duration_days=12),
            headers=lead,
        )

        assert response.status_code == 200
        assert (response.json()["name"], response.json()["estimated_duration_days"]) == (
            "Mampostería PB",
            12,
        )

    def test_saving_without_changing_the_name_is_not_a_conflict(
        self, client, world, team, lead, task
    ):
        response = client.put(tasks_url(world, task_id=task), json=body(), headers=lead)

        assert response.status_code == 200

    def test_the_status_cannot_be_changed_through_the_form(self, client, world, team, lead, task):
        """A field the schema does not have is simply not read."""
        response = client.put(
            tasks_url(world, task_id=task), json=body(status="finished"), headers=lead
        )

        assert response.json()["status"] == "pending"

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, task, auth_header, role):
        response = client.put(
            tasks_url(world, task_id=task), json=body(), headers=auth_header(team[role])
        )

        assert response.status_code == 403

    def test_a_removed_task_is_a_404(self, client, world, team, lead, add_task):
        removed = add_task(world.project_a, world.firm_a, is_active=False)

        response = client.put(tasks_url(world, task_id=removed), json=body(), headers=lead)

        assert response.status_code == 404

    def test_a_task_of_another_work_of_the_same_firm_is_a_404(
        self, client, world, team, lead, add_task, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        theirs = add_task(other, world.firm_a)

        response = client.put(tasks_url(world, task_id=theirs), json=body(), headers=lead)

        assert response.status_code == 404


class TestDelete:
    def test_removing_a_task_gives_its_lines_back(
        self, client, world, team, lead, task, recipe_id, add_takeoff_line
    ):
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task)

        response = client.delete(tasks_url(world, task_id=task), headers=lead)

        assert response.status_code == 204
        planning = client.get(tasks_url(world), headers=lead).json()
        assert planning["tasks"] == []
        assert (planning["unassigned_cost"], planning["total_cost"]) == (WALL_120, WALL_120)

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, task, auth_header, role):
        response = client.delete(tasks_url(world, task_id=task), headers=auth_header(team[role]))

        assert response.status_code == 403

    def test_removing_it_twice_is_a_404(self, client, world, team, lead, task):
        client.delete(tasks_url(world, task_id=task), headers=lead)

        assert client.delete(tasks_url(world, task_id=task), headers=lead).status_code == 404


class TestTransitions:
    def url(self, world, task: int) -> str:
        return f"{tasks_url(world, task_id=task)}/transitions"

    def test_a_task_goes_through_its_whole_life(self, client, world, team, lead, task):
        """Every action of HU-13, in an order that visits all six."""
        statuses = []
        for action in (
            "start",
            "undo_start",
            "start",
            "pause",
            "resume",
            "finish",
            "reopen",
            "finish",
        ):
            response = client.post(self.url(world, task), json={"action": action}, headers=lead)
            assert response.status_code == 200, action
            statuses.append(response.json()["status"])

        assert statuses == [
            "in_progress",
            "pending",
            "in_progress",
            "paused",
            "in_progress",
            "finished",
            "in_progress",
            "finished",
        ]

    def test_starting_and_finishing_record_the_dates_sent(self, client, world, team, lead, task):
        client.post(
            self.url(world, task), json={"action": "start", "on_date": "2026-10-01"}, headers=lead
        )
        finished = client.post(
            self.url(world, task), json={"action": "finish", "on_date": "2026-10-05"}, headers=lead
        ).json()

        assert (finished["actual_start_date"], finished["actual_end_date"]) == (
            "2026-10-01",
            "2026-10-05",
        )

    def test_starting_without_a_date_records_one(self, client, world, team, lead, task):
        started = client.post(self.url(world, task), json={"action": "start"}, headers=lead).json()

        assert started["actual_start_date"] is not None

    def test_an_action_the_status_does_not_allow_is_a_409_that_says_so(
        self, client, world, team, lead, task
    ):
        response = client.post(self.url(world, task), json={"action": "pause"}, headers=lead)

        assert response.status_code == 409
        assert response.json()["detail"] == invalid_transition("pending", "pause")

    def test_a_double_start_is_refused_the_second_time(self, client, world, team, lead, task):
        client.post(self.url(world, task), json={"action": "start"}, headers=lead)

        response = client.post(self.url(world, task), json={"action": "start"}, headers=lead)

        assert response.status_code == 409

    def test_finishing_before_the_start_is_a_409(self, client, world, team, lead, task):
        client.post(
            self.url(world, task), json={"action": "start", "on_date": "2026-10-05"}, headers=lead
        )

        response = client.post(
            self.url(world, task), json={"action": "finish", "on_date": "2026-10-01"}, headers=lead
        )

        assert response.status_code == 409
        assert response.json()["detail"] == END_BEFORE_START

    def test_a_date_on_an_action_that_records_none_is_a_409(self, client, world, team, lead, task):
        client.post(self.url(world, task), json={"action": "start"}, headers=lead)

        response = client.post(
            self.url(world, task), json={"action": "pause", "on_date": "2026-10-01"}, headers=lead
        )

        assert response.status_code == 409
        assert response.json()["detail"] == DATE_NOT_EXPECTED

    def test_an_action_that_does_not_exist_is_a_422(self, client, world, team, lead, task):
        response = client.post(self.url(world, task), json={"action": "cancel"}, headers=lead)

        assert response.status_code == 422

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, task, auth_header, role):
        response = client.post(
            self.url(world, task), json={"action": "start"}, headers=auth_header(team[role])
        )

        assert response.status_code == 403


class TestActualDates:
    def url(self, world, task: int) -> str:
        return f"{tasks_url(world, task_id=task)}/actual-dates"

    @pytest.fixture
    def started(self, world, add_task) -> int:
        return add_task(
            world.project_a, world.firm_a, status="in_progress", actual_start="2026-10-05"
        )

    def test_the_start_of_a_started_task_is_corrected(self, client, world, team, lead, started):
        response = client.put(
            self.url(world, started),
            json={"actual_start_date": "2026-10-01", "actual_end_date": None},
            headers=lead,
        )

        assert response.status_code == 200
        assert response.json()["actual_start_date"] == "2026-10-01"
        assert response.json()["status"] == "in_progress"

    def test_a_date_the_status_does_not_allow_is_a_409(self, client, world, team, lead, started):
        response = client.put(
            self.url(world, started),
            json={"actual_start_date": "2026-10-01", "actual_end_date": "2026-10-03"},
            headers=lead,
        )

        assert response.status_code == 409

    def test_both_keys_have_to_be_sent(self, client, world, team, lead, started):
        response = client.put(
            self.url(world, started), json={"actual_start_date": "2026-10-01"}, headers=lead
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, started, auth_header, role):
        response = client.put(
            self.url(world, started),
            json={"actual_start_date": "2026-10-01", "actual_end_date": None},
            headers=auth_header(team[role]),
        )

        assert response.status_code == 403


class TestTaskLines:
    def url(self, world, task: int) -> str:
        return f"{tasks_url(world, task_id=task)}/lines"

    def test_assigning_lines_gives_the_task_their_cost(self, client, world, team, lead, task, wall):
        response = client.put(self.url(world, task), json={"line_ids": [wall]}, headers=lead)

        assert response.status_code == 200
        assert response.json()["cost"] == WALL_120
        planning = client.get(tasks_url(world), headers=lead).json()
        assert (planning["unassigned_cost"], planning["total_cost"]) == ("0.00", WALL_120)

    def test_an_empty_selection_gives_them_back(self, client, world, team, lead, task, wall):
        client.put(self.url(world, task), json={"line_ids": [wall]}, headers=lead)

        response = client.put(self.url(world, task), json={"line_ids": []}, headers=lead)

        assert response.json()["cost"] == "0.00"

    def test_a_line_that_is_not_in_this_take_off_is_a_409(self, client, world, team, lead, task):
        response = client.put(self.url(world, task), json={"line_ids": [999_999]}, headers=lead)

        assert response.status_code == 409
        assert response.json()["detail"] == LINE_NOT_AVAILABLE

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, task, wall, auth_header, role):
        response = client.put(
            self.url(world, task), json={"line_ids": [wall]}, headers=auth_header(team[role])
        )

        assert response.status_code == 403


class TestLineTaskFromTheTakeoff:
    """HU-13: "en el cómputo, cada línea muestra a qué tarea está asignada y se
    puede cambiar desde ahí"."""

    def takeoff(self, client, world, headers) -> list[dict]:
        url = f"/firms/{world.firm_a}/projects/{world.project_a}/takeoff"
        return client.get(url, headers=headers).json()["lines"]

    def test_a_line_is_assigned_and_the_take_off_shows_it(
        self, client, world, team, lead, task, wall
    ):
        response = client.put(line_task_url(world, wall), json={"task_id": task}, headers=lead)

        assert response.status_code == 200
        assert response.json()["task"] == {"id": task, "name": "Mampostería"}
        assert self.takeoff(client, world, lead)[0]["task"] == {"id": task, "name": "Mampostería"}

    def test_null_unassigns_it(self, client, world, team, lead, task, wall):
        client.put(line_task_url(world, wall), json={"task_id": task}, headers=lead)

        response = client.put(line_task_url(world, wall), json={"task_id": None}, headers=lead)

        assert response.json()["task"] is None

    def test_an_unassigned_line_reads_as_null(self, client, world, team, lead, wall):
        assert self.takeoff(client, world, lead)[0]["task"] is None

    def test_the_client_sees_which_task_a_line_is_in(
        self, client, world, team, lead, task, wall, auth_header
    ):
        client.put(line_task_url(world, wall), json={"task_id": task}, headers=lead)

        lines = self.takeoff(client, world, auth_header(team["client"]))

        assert lines[0]["task"]["name"] == "Mampostería"

    def test_a_removed_task_is_a_409(self, client, world, team, lead, wall, add_task):
        removed = add_task(world.project_a, world.firm_a, "Vieja", is_active=False)

        response = client.put(line_task_url(world, wall), json={"task_id": removed}, headers=lead)

        assert response.status_code == 409
        assert response.json()["detail"] == TASK_NOT_AVAILABLE

    def test_a_task_of_another_work_is_the_same_409_and_not_a_500(
        self, client, world, team, lead, wall, add_task, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        theirs = add_task(other, world.firm_a)

        response = client.put(line_task_url(world, wall), json={"task_id": theirs}, headers=lead)

        assert response.status_code == 409
        assert response.json()["detail"] == TASK_NOT_AVAILABLE

    def test_a_line_that_does_not_exist_is_a_404(self, client, world, team, lead, task):
        response = client.put(line_task_url(world, 999_999), json={"task_id": task}, headers=lead)

        assert response.status_code == 404

    def test_the_key_has_to_be_sent(self, client, world, team, lead, wall):
        """An empty body is not "unassign"."""
        response = client.put(line_task_url(world, wall), json={}, headers=lead)

        assert response.status_code == 422

    @pytest.mark.parametrize("role", NOT_WRITERS)
    def test_the_others_get_403(self, client, world, team, task, wall, auth_header, role):
        response = client.put(
            line_task_url(world, wall), json={"task_id": task}, headers=auth_header(team[role])
        )

        assert response.status_code == 403
