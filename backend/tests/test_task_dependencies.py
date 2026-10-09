"""Pins the rules about what waits for what (HU-14), against the session and without HTTP.

Rules 1, 2, 5 and 7 of ADR-009 section 10: no cycles, no start while a
predecessor is unfinished, removing a task deletes its dependencies, and a
dependency only joins live tasks of the same work. The status codes are the API
tests' business; here it is what gets written, and that a refused change writes
nothing.
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.models import Project, ProjectTask
from app.services.tasks import (
    PREDECESSOR_NOT_AVAILABLE,
    SELF_DEPENDENCY,
    TaskError,
    blocked_start,
    create_task,
    dependency_cycle,
    remove_task,
    transition,
    update_task,
)

TODAY = date(2026, 10, 9)


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch) -> None:
    monkeypatch.setattr("app.services.tasks.today", lambda: TODAY)


@pytest.fixture
def project(db_session, world, add_project_member) -> Project:
    add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
    return db_session.get(Project, world.project_a)


def edges_of(db_session, project_id: int) -> set[tuple[int, int]]:
    """Every dependency row of a work, read straight from the table."""
    return {
        tuple(row)
        for row in db_session.execute(
            text(
                "SELECT predecessor_id, successor_id FROM project_task_dependency"
                " WHERE project_id = :p"
            ),
            {"p": project_id},
        )
    }


def new_task(db_session, project: Project, name: str, **fields) -> ProjectTask:
    return create_task(db_session, project, name=name, estimated_duration_days=3, **fields)


def edit(db_session, project: Project, task: ProjectTask, predecessor_ids) -> ProjectTask:
    """Save the form unchanged except for the predecessors."""
    return update_task(
        db_session,
        project,
        task,
        name=task.name,
        estimated_duration_days=task.estimated_duration_days,
        predecessor_ids=predecessor_ids,
    )


class TestSettingPredecessors:
    def test_a_task_can_be_created_with_its_predecessors(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        assert edges_of(db_session, project.id) == {(a.id, b.id)}

    def test_editing_replaces_the_predecessors(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Instalaciones")
        c = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        edit(db_session, project, c, [b.id])

        assert edges_of(db_session, project.id) == {(b.id, c.id)}

    def test_an_empty_list_clears_them(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        edit(db_session, project, b, [])

        assert edges_of(db_session, project.id) == set()

    def test_leaving_them_out_keeps_them(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        edit(db_session, project, b, None)

        assert edges_of(db_session, project.id) == {(a.id, b.id)}

    def test_a_repeated_predecessor_is_one_dependency(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id, a.id])

        assert edges_of(db_session, project.id) == {(a.id, b.id)}

    def test_a_task_cannot_be_its_own_predecessor(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")

        with pytest.raises(TaskError) as refused:
            edit(db_session, project, a, [a.id])

        assert refused.value.detail == SELF_DEPENDENCY
        assert edges_of(db_session, project.id) == set()

    def test_a_removed_task_cannot_be_a_predecessor(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        remove_task(db_session, a)

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        assert refused.value.detail == PREDECESSOR_NOT_AVAILABLE

    def test_a_task_of_another_work_gets_the_same_refusal(
        self, db_session, project, world, add_task, new_project
    ):
        other = new_project(world.firm_a, world.account_a, "Casa Este")
        elsewhere = add_task(other, world.firm_a)
        b = new_task(db_session, project, "Mampostería")

        with pytest.raises(TaskError) as refused:
            edit(db_session, project, b, [elsewhere])

        assert refused.value.detail == PREDECESSOR_NOT_AVAILABLE
        assert edges_of(db_session, project.id) == set()

    def test_a_task_of_another_firm_gets_the_same_refusal(
        self, db_session, project, world, add_task
    ):
        elsewhere = add_task(world.project_b, world.firm_b)

        with pytest.raises(TaskError) as refused:
            new_task(db_session, project, "Mampostería", predecessor_ids=[elsewhere])

        assert refused.value.detail == PREDECESSOR_NOT_AVAILABLE


class TestCycles:
    def test_a_direct_cycle_is_refused_and_named(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        with pytest.raises(TaskError) as refused:
            edit(db_session, project, a, [b.id])

        assert refused.value.detail == dependency_cycle(["Cimientos", "Mampostería", "Cimientos"])
        assert edges_of(db_session, project.id) == {(a.id, b.id)}

    def test_a_longer_cycle_is_refused_too(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])
        c = new_task(db_session, project, "Revoque", predecessor_ids=[b.id])

        with pytest.raises(TaskError) as refused:
            edit(db_session, project, a, [c.id])

        assert refused.value.detail == dependency_cycle(
            ["Cimientos", "Mampostería", "Revoque", "Cimientos"]
        )

    def test_a_diamond_is_not_a_cycle(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])
        c = new_task(db_session, project, "Instalaciones", predecessor_ids=[a.id])

        d = new_task(db_session, project, "Revoque", predecessor_ids=[b.id, c.id])

        assert (b.id, d.id) in edges_of(db_session, project.id)


class TestRemoving:
    def test_removing_a_task_deletes_its_dependencies_both_ways(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])
        c = new_task(db_session, project, "Revoque", predecessor_ids=[b.id])

        remove_task(db_session, b)

        assert edges_of(db_session, project.id) == set()
        # c no longer waits for anything, so it can start.
        transition(db_session, c, "start")
        assert c.status == "in_progress"


class TestStarting:
    def test_a_task_cannot_start_while_a_predecessor_is_pending(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])

        with pytest.raises(TaskError) as refused:
            transition(db_session, b, "start")

        assert refused.value.detail == blocked_start("Mampostería", ["Cimientos"])
        assert (b.status, b.actual_start_date) == ("pending", None)

    def test_the_refusal_names_every_unfinished_predecessor(
        self, db_session, project, world, add_task
    ):
        done = add_task(
            world.project_a,
            world.firm_a,
            "Replanteo",
            status="finished",
            actual_start="2026-10-01",
            actual_end="2026-10-02",
        )
        running = add_task(
            world.project_a,
            world.firm_a,
            "Cimientos",
            status="in_progress",
            actual_start="2026-10-05",
        )
        waiting = new_task(db_session, project, "Instalaciones")
        b = new_task(
            db_session, project, "Mampostería", predecessor_ids=[done, running, waiting.id]
        )

        with pytest.raises(TaskError) as refused:
            transition(db_session, b, "start")

        assert refused.value.detail == (
            "No se puede iniciar «Mampostería» hasta que finalicen «Cimientos» y «Instalaciones»."
        )

    def test_a_task_starts_once_its_predecessors_finished(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])
        transition(db_session, a, "start")
        transition(db_session, a, "finish")

        transition(db_session, b, "start")

        assert b.status == "in_progress"

    def test_reopening_a_predecessor_whose_successor_started_is_allowed(self, db_session, project):
        a = new_task(db_session, project, "Cimientos")
        b = new_task(db_session, project, "Mampostería", predecessor_ids=[a.id])
        transition(db_session, a, "start")
        transition(db_session, a, "finish")
        transition(db_session, b, "start")

        transition(db_session, a, "reopen")

        assert (a.status, b.status) == ("in_progress", "in_progress")

    def test_the_block_reads_the_singular_with_one_predecessor(self):
        assert blocked_start("Revoque", ["Mampostería"]) == (
            "No se puede iniciar «Revoque» hasta que finalice «Mampostería»."
        )
