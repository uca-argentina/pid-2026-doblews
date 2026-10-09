"""Pins the rules for writing a work's planning, against the session and without HTTP.

The rules of ADR-009 section 10 that HU-13 brings in — the ones no constraint
can hold, because each has to look at another table. The status codes they
become are the API tests' business; here it is what gets written, and that a
refused change writes nothing.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

from app.models import Project, ProjectRecipe, ProjectTask
from app.repositories.project_recipe import ProjectRecipeRepository
from app.services.budget_versions import load_version, save_version
from app.services.project import update_project
from app.services.project_team import change_team_role, remove_team_member
from app.services.tasks import (
    ASSIGNEE_NOT_ALLOWED,
    LINE_NOT_AVAILABLE,
    NAME_TAKEN,
    TaskError,
    assign_lines,
    create_task,
    list_assignees,
    remove_task,
    set_line_task,
    unassign_open_tasks,
    update_task,
)

WALL = "Pared de ladrillo común 15cm"


def tasks_in(db_session, project_id: int) -> list[tuple]:
    """(name, status, assignee, is_active) of every row, removed ones included."""
    return [
        tuple(row)
        for row in db_session.execute(
            text(
                "SELECT name, status, assignee_account_id, is_active FROM project_task"
                " WHERE project_id = :p ORDER BY id"
            ),
            {"p": project_id},
        )
    ]


def task_of(db_session, line_id: int) -> int | None:
    """The task a take-off line points at, read straight from the table."""
    return db_session.execute(
        text("SELECT task_id FROM project_recipe WHERE id = :id"), {"id": line_id}
    ).scalar_one()


def assignee_of(db_session, task_id: int) -> int | None:
    return db_session.execute(
        text("SELECT assignee_account_id FROM project_task WHERE id = :id"), {"id": task_id}
    ).scalar_one()


@pytest.fixture
def project(db_session, world, add_project_member) -> Project:
    """Firm A's work, led by Ana and with Alba as a collaborator.

    Both hold project.task.manage, so either can be made an assignee.
    """
    add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
    add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
    return db_session.get(Project, world.project_a)


@pytest.fixture
def on_team(world, new_member, add_project_member):
    """Someone new on firm A's roster and on the work, with any project role."""

    def _add(email: str, project_role: str, *, firm_role: str = "architect") -> int:
        account = new_member(world.firm_a, email, firm_role)
        add_project_member(world.project_a, account, world.firm_a, project_role)
        return account

    return _add


def new_task(db_session, project: Project, name: str = "Mampostería", **fields) -> ProjectTask:
    return create_task(db_session, project, name=name, estimated_duration_days=10, **fields)


class TestCreate:
    def test_a_task_is_born_pending_and_with_no_dates(self, db_session, project):
        task = new_task(db_session, project)

        assert task.id is not None
        assert task.status == "pending"
        assert (task.actual_start_date, task.actual_end_date) == (None, None)
        assert tasks_in(db_session, project.id) == [("Mampostería", "pending", None, True)]

    def test_the_task_takes_the_firm_of_its_work(self, db_session, project, world):
        assert new_task(db_session, project).firm_id == world.firm_a

    def test_a_name_already_in_use_is_refused_whatever_the_case(self, db_session, project):
        new_task(db_session, project, "Mampostería")

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, "MAMPOSTERÍA")

        assert refused.value.detail == NAME_TAKEN
        assert len(tasks_in(db_session, project.id)) == 1

    def test_the_name_of_a_removed_task_can_be_used_again(self, db_session, project):
        remove_task(db_session, new_task(db_session, project, "Mampostería"))

        new_task(db_session, project, "Mampostería")

        assert [row[3] for row in tasks_in(db_session, project.id)] == [False, True]


class TestAssignee:
    """Rule 4 of ADR-009 section 10: the assignee holds project.task.manage."""

    def test_a_lead_or_a_collaborator_can_be_assigned(self, db_session, project, world):
        new_task(db_session, project, "Cimientos", assignee_account_id=world.account_a)
        new_task(db_session, project, "Techos", assignee_account_id=world.account_a2)

        assert [row[2] for row in tasks_in(db_session, project.id)] == [
            world.account_a,
            world.account_a2,
        ]

    @pytest.mark.parametrize("project_role", ["viewer", "client"])
    def test_someone_who_cannot_manage_the_planning_is_refused(
        self, db_session, project, on_team, project_role
    ):
        # A firm client is the only one who may be a project client (ADR-002 11.2).
        firm_role = "client" if project_role == "client" else "architect"
        account = on_team("vera@test.com", project_role, firm_role=firm_role)

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, assignee_account_id=account)

        assert refused.value.detail == ASSIGNEE_NOT_ALLOWED
        assert tasks_in(db_session, project.id) == []

    def test_someone_of_the_firm_who_is_not_on_the_team_is_refused(
        self, db_session, project, world, new_member
    ):
        outsider = new_member(world.firm_a, "omar@test.com", "architect")

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, assignee_account_id=outsider)

        assert refused.value.detail == ASSIGNEE_NOT_ALLOWED

    def test_someone_of_another_firm_gets_the_same_refusal(self, db_session, project, world):
        """Not an IntegrityError from the foreign key, which would be a 500."""
        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, assignee_account_id=world.account_b)

        assert refused.value.detail == ASSIGNEE_NOT_ALLOWED

    def test_someone_who_left_the_roster_is_refused(self, db, db_session, project, world):
        """Their project_member row is still there and grants nothing (ADR-002 11.3)."""
        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"),
            {"a": world.account_a2},
        )

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, assignee_account_id=world.account_a2)

        assert refused.value.detail == ASSIGNEE_NOT_ALLOWED


class TestListAssignees:
    def test_offers_whoever_may_manage_the_planning_by_name(
        self, db_session, project, world, on_team
    ):
        on_team("vera@test.com", "viewer")
        on_team("carla@test.com", "client", firm_role="client")

        offered = list_assignees(db_session, project)

        assert [(person.account_id, person.name) for person in offered] == [
            (world.account_a2, "alba"),
            (world.account_a, "ana"),
        ]

    def test_does_not_offer_someone_who_left_the_roster(self, db, db_session, project, world):
        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"),
            {"a": world.account_a2},
        )

        offered = list_assignees(db_session, project)

        assert [person.account_id for person in offered] == [world.account_a]


class TestUpdate:
    def test_every_field_of_the_form_is_replaced(self, db_session, project, world):
        task = new_task(
            db_session,
            project,
            description="Con ladrillo común",
            assignee_account_id=world.account_a,
        )

        update_task(db_session, project, task, name="Mampostería PB", estimated_duration_days=12)

        assert (task.name, task.estimated_duration_days) == ("Mampostería PB", 12)
        # Left out of the call, so cleared: the form sends the whole task.
        assert (task.description, task.assignee_account_id) == (None, None)

    def test_a_task_can_be_saved_without_changing_its_name(self, db_session, project):
        task = new_task(db_session, project, "Mampostería")

        update_task(db_session, project, task, name="Mampostería", estimated_duration_days=3)

        assert task.estimated_duration_days == 3

    def test_renaming_onto_another_tasks_name_is_refused(self, db_session, project):
        new_task(db_session, project, "Cimientos")
        task = new_task(db_session, project, "Mampostería")

        with pytest.raises(TaskError) as refused:
            update_task(db_session, project, task, name="cimientos", estimated_duration_days=10)

        assert refused.value.detail == NAME_TAKEN

    def test_a_new_assignee_is_checked(self, db_session, project, on_team):
        task = new_task(db_session, project)
        viewer = on_team("vera@test.com", "viewer")

        with pytest.raises(TaskError) as refused:
            update_task(
                db_session,
                project,
                task,
                name=task.name,
                estimated_duration_days=10,
                assignee_account_id=viewer,
            )

        assert refused.value.detail == ASSIGNEE_NOT_ALLOWED

    def test_an_assignee_whose_role_was_lowered_keeps_the_task_when_it_is_edited(
        self, db_session, project, world
    ):
        """The rule is about the moment of assigning (ADR-009 section 6). Saving
        the form with the assignee it already had must not be refused."""
        task = new_task(db_session, project, assignee_account_id=world.account_a2)
        change_team_role(
            db_session,
            project,
            actor_id=world.account_a,
            account_id=world.account_a2,
            role_code="viewer",
        )

        update_task(
            db_session,
            project,
            task,
            name="Mampostería PB",
            estimated_duration_days=10,
            assignee_account_id=world.account_a2,
        )

        assert task.assignee_account_id == world.account_a2


class TestRemove:
    """Rule 5 of ADR-009 section 10."""

    def test_the_task_is_deactivated_not_deleted(self, db_session, project):
        task = new_task(db_session, project)

        remove_task(db_session, task)

        assert tasks_in(db_session, project.id) == [("Mampostería", "pending", None, False)]

    def test_its_lines_go_back_to_unassigned_and_stay_in_the_take_off(
        self, db_session, project, world, recipe_id, add_takeoff_line
    ):
        task = new_task(db_session, project)
        line = add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task.id)

        remove_task(db_session, task)

        assert task_of(db_session, line) is None
        still_there = db_session.execute(
            text("SELECT is_active FROM project_recipe WHERE id = :id"), {"id": line}
        ).scalar_one()
        assert still_there is True

    def test_the_lines_of_another_task_are_left_alone(
        self, db_session, project, world, recipe_id, add_takeoff_line
    ):
        removed = new_task(db_session, project, "Cimientos")
        kept = new_task(db_session, project, "Mampostería")
        line = add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=kept.id)

        remove_task(db_session, removed)

        assert task_of(db_session, line) == kept.id

    def test_a_started_task_can_be_removed_too(self, db_session, world, project, add_task):
        task = db_session.get(
            ProjectTask,
            add_task(
                world.project_a, world.firm_a, status="in_progress", actual_start="2026-10-01"
            ),
        )

        remove_task(db_session, task)

        assert tasks_in(db_session, project.id)[0][3] is False


class TestAssignLines:
    """Rule 7 of ADR-009 section 10, from the task's side."""

    @pytest.fixture
    def line(self, world, recipe_id, add_takeoff_line):
        def _add(quantity: str = "120", **fields) -> int:
            return add_takeoff_line(
                world.project_a, world.firm_a, recipe_id[WALL], quantity, **fields
            )

        return _add

    def test_the_lines_named_become_the_tasks_lines(self, db_session, project, line):
        task = new_task(db_session, project)
        first, second, other = line("70"), line("50"), line("10")

        assign_lines(db_session, task, [first, second])

        assert [task_of(db_session, each) for each in (first, second, other)] == [
            task.id,
            task.id,
            None,
        ]

    def test_it_replaces_the_selection_rather_than_adding_to_it(self, db_session, project, line):
        task = new_task(db_session, project)
        dropped, kept, added = line("70", task=task.id), line("50", task=task.id), line("10")

        assign_lines(db_session, task, [kept, added])

        assert [task_of(db_session, each) for each in (dropped, kept, added)] == [
            None,
            task.id,
            task.id,
        ]

    def test_an_empty_selection_unassigns_everything(self, db_session, project, line):
        task = new_task(db_session, project)
        only = line(task=task.id)

        assign_lines(db_session, task, [])

        assert task_of(db_session, only) is None

    def test_a_line_of_another_task_is_moved(self, db_session, project, line):
        """A line is in one task or in none."""
        source = new_task(db_session, project, "Cimientos")
        target = new_task(db_session, project, "Mampostería")
        moved = line(task=source.id)

        assign_lines(db_session, target, [moved])

        assert task_of(db_session, moved) == target.id

    def test_a_removed_line_is_refused_and_nothing_changes(self, db_session, project, line):
        task = new_task(db_session, project)
        live, removed = line("70"), line("50", is_active=False)

        with pytest.raises(TaskError) as refused:
            assign_lines(db_session, task, [live, removed])

        assert refused.value.detail == LINE_NOT_AVAILABLE
        assert task_of(db_session, live) is None

    def test_a_line_of_another_work_gets_the_same_refusal(
        self, db_session, project, world, recipe_id, add_takeoff_line, new_project
    ):
        """Not an IntegrityError from the composite foreign key."""
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        theirs = add_takeoff_line(other, world.firm_a, recipe_id[WALL], "120")
        task = new_task(db_session, project)

        with pytest.raises(TaskError) as refused:
            assign_lines(db_session, task, [theirs])

        assert refused.value.detail == LINE_NOT_AVAILABLE

    def test_a_line_that_does_not_exist_gets_the_same_refusal(self, db_session, project):
        task = new_task(db_session, project)

        with pytest.raises(TaskError) as refused:
            assign_lines(db_session, task, [999_999])

        assert refused.value.detail == LINE_NOT_AVAILABLE

    def test_one_line_is_assigned_and_unassigned_from_the_take_off(self, db_session, project, line):
        """The take-off screen's side of the same rule."""
        task = new_task(db_session, project)
        loaded = db_session.get(ProjectRecipe, line())

        set_line_task(db_session, loaded, task)
        assert task_of(db_session, loaded.id) == task.id

        set_line_task(db_session, loaded, None)
        assert task_of(db_session, loaded.id) is None


class TestLeavingTheTeam:
    """Rule 6 of ADR-009 section 10."""

    @pytest.fixture
    def alba_tasks(self, world, add_task) -> dict[str, int]:
        """One task of Alba's in each status."""
        return {
            "pending": add_task(
                world.project_a, world.firm_a, "Pendiente", assignee=world.account_a2
            ),
            "in_progress": add_task(
                world.project_a,
                world.firm_a,
                "En curso",
                status="in_progress",
                actual_start="2026-10-01",
                assignee=world.account_a2,
            ),
            "paused": add_task(
                world.project_a,
                world.firm_a,
                "Pausada",
                status="paused",
                actual_start="2026-10-01",
                assignee=world.account_a2,
            ),
            "finished": add_task(
                world.project_a,
                world.firm_a,
                "Finalizada",
                status="finished",
                actual_start="2026-10-01",
                actual_end="2026-10-05",
                assignee=world.account_a2,
            ),
        }

    def test_being_taken_off_the_team_frees_the_unfinished_tasks_only(
        self, db_session, project, world, alba_tasks
    ):
        remove_team_member(
            db_session, project, actor_id=world.account_a, account_id=world.account_a2
        )

        assert {status: assignee_of(db_session, task) for status, task in alba_tasks.items()} == {
            "pending": None,
            "in_progress": None,
            "paused": None,
            "finished": world.account_a2,
        }

    def test_the_tasks_of_everyone_else_are_left_alone(self, db_session, project, world, add_task):
        anas = add_task(world.project_a, world.firm_a, assignee=world.account_a)

        remove_team_member(
            db_session, project, actor_id=world.account_a, account_id=world.account_a2
        )

        assert assignee_of(db_session, anas) == world.account_a

    def test_the_same_person_keeps_their_tasks_on_another_work(
        self, db_session, project, world, add_task, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Otra")
        elsewhere = add_task(other, world.firm_a, assignee=world.account_a2)

        unassign_open_tasks(db_session, project_id=project.id, account_id=world.account_a2)

        assert assignee_of(db_session, elsewhere) == world.account_a2

    def test_a_lowered_role_keeps_the_tasks(self, db_session, project, world, alba_tasks):
        """Changing a role is not leaving the team (ADR-009 section 6)."""
        change_team_role(
            db_session,
            project,
            actor_id=world.account_a,
            account_id=world.account_a2,
            role_code="viewer",
        )

        assert assignee_of(db_session, alba_tasks["pending"]) == world.account_a2

    def test_clearing_the_client_from_the_works_form_frees_their_tasks(
        self, db_session, project, world, on_team, add_task
    ):
        """The other place a project_member row is deleted. Reaching it takes a
        client who somehow holds a task, which the assignee rule forbids today;
        the hook is there so the rule does not depend on that."""
        client = on_team("carla@test.com", "client", firm_role="client")
        task = add_task(world.project_a, world.firm_a, assignee=client)

        update_project(db_session, project, name=project.name, client_account_id=None)

        assert assignee_of(db_session, task) is None

    def test_saving_the_works_form_with_the_same_client_frees_nothing(
        self, db_session, project, world, on_team, add_task
    ):
        client = on_team("carla@test.com", "client", firm_role="client")
        task = add_task(world.project_a, world.firm_a, assignee=client)

        update_project(db_session, project, name=project.name, client_account_id=client)

        assert assignee_of(db_session, task) == client


class TestLoadingABudgetVersion:
    def test_the_lines_loaded_from_a_version_come_back_unassigned(
        self, db_session, project, world, recipe_id, add_takeoff_line
    ):
        """HU-12 replaces the take-off lines with new ones copied from the
        version, and a version does not record tasks (ADR-009, pending for
        HU-19). So the task is left costing nothing and everything is unassigned."""
        task = new_task(db_session, project)
        add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120", task=task.id)
        repository = ProjectRecipeRepository(db_session, firm_id=world.firm_a)
        before = repository.cost_by_task(project.id)
        version = save_version(db_session, project, account_id=world.account_a)

        load_version(db_session, project, version)

        assert before == {task.id: Decimal("3877800.00")}
        assert repository.cost_by_task(project.id) == {None: Decimal("3877800.00")}
        assert [line.task for line in repository.lines(project.id)] == [None]
