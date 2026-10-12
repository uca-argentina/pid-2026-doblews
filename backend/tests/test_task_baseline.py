"""Pins fixing the planning and what the progress is then compared against (HU-16).

Against the session and without HTTP. The arithmetic is pinned in
test_progress.py; here it is what fix_baseline copies, when it refuses, and
which tasks measure_progress counts.

October 2026: the 5th is a Monday. Today is frozen and moved by the tests.
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.models import Project, ProjectTask
from app.repositories.project_task import ProjectTaskRepository
from app.services.tasks import (
    BASELINE_NEEDS_START,
    BASELINE_NEEDS_TASKS,
    TaskError,
    fix_baseline,
    measure_progress,
    remove_task,
    set_progress,
    transition,
)

MON = date(2026, 10, 5)
TUE = date(2026, 10, 6)
WED = date(2026, 10, 7)
THU = date(2026, 10, 8)
FRI = date(2026, 10, 9)


@pytest.fixture
def on(monkeypatch):
    """Set what day it is, for the schedule and for the comparison alike."""

    def _on(day: date) -> None:
        monkeypatch.setattr("app.services.tasks.today", lambda: day)

    _on(MON)
    return _on


@pytest.fixture
def work(db_session, world, on) -> Project:
    """Work A, starting on Monday the 5th."""
    project = db_session.get(Project, world.project_a)
    project.estimated_start_date = MON
    db_session.flush()
    return project


@pytest.fixture
def chain(db_session, world, add_task) -> tuple[ProjectTask, ProjectTask]:
    """Cimientos, three days, and then Mampostería, two: Monday to Friday."""
    first = add_task(world.project_a, world.firm_a, "Cimientos", duration=3)
    second = add_task(world.project_a, world.firm_a, "Mampostería", duration=2)
    db_session.execute(
        text(
            "INSERT INTO project_task_dependency (predecessor_id, successor_id, project_id)"
            " VALUES (:a, :b, :p)"
        ),
        {"a": first, "b": second, "p": world.project_a},
    )
    return db_session.get(ProjectTask, first), db_session.get(ProjectTask, second)


def report(db_session, project: Project):
    entries = ProjectTaskRepository(db_session, firm_id=project.firm_id).tasks(project.id)
    return measure_progress(entries)


class TestFixing:
    def test_it_copies_the_planned_dates_of_every_task_and_of_the_work(
        self, db_session, work, chain
    ):
        first, second = chain

        fix_baseline(db_session, work)

        assert (first.baseline_start_date, first.baseline_end_date) == (MON, WED)
        assert (second.baseline_start_date, second.baseline_end_date) == (THU, FRI)
        assert (work.baseline_set_on, work.baseline_end_date) == (MON, FRI)

    def test_the_copy_stays_when_the_planned_dates_move(self, db_session, work, chain, on):
        """The point of it: a week later nothing started, and the plan slid."""
        first, _ = chain
        fix_baseline(db_session, work)

        on(date(2026, 10, 12))

        db_session.refresh(first)
        assert (first.baseline_start_date, first.baseline_end_date) == (MON, WED)
        assert work.baseline_end_date == FRI

    def test_fixing_again_replaces_it(self, db_session, work, chain, on):
        first, _ = chain
        fix_baseline(db_session, work)

        on(date(2026, 10, 12))
        fix_baseline(db_session, work)

        assert first.baseline_start_date == date(2026, 10, 12)
        assert (work.baseline_set_on, work.baseline_end_date) == (
            date(2026, 10, 12),
            date(2026, 10, 16),
        )

    def test_a_started_task_is_fixed_with_its_actual_start(self, db_session, work, chain, on):
        """What happened replaces what was planned (ADR-009 section 4)."""
        first, _ = chain
        on(TUE)
        transition(db_session, first, "start", on_date=MON)

        fix_baseline(db_session, work)

        assert (first.baseline_start_date, first.baseline_end_date) == (MON, WED)

    def test_a_work_with_no_start_date_is_refused(self, db_session, world, chain, on):
        project = db_session.get(Project, world.project_a)

        with pytest.raises(TaskError) as refused:
            fix_baseline(db_session, project)

        assert refused.value.detail == BASELINE_NEEDS_START
        assert project.baseline_set_on is None

    def test_a_work_with_no_tasks_is_refused(self, db_session, work):
        with pytest.raises(TaskError) as refused:
            fix_baseline(db_session, work)

        assert refused.value.detail == BASELINE_NEEDS_TASKS
        assert work.baseline_set_on is None

    def test_a_removed_task_is_not_fixed(self, db_session, work, chain):
        first, second = chain
        remove_task(db_session, second)

        fix_baseline(db_session, work)

        assert second.baseline_start_date is None
        assert work.baseline_end_date == WED


class TestComparing:
    def test_without_a_fixed_planning_there_is_nothing_to_compare(self, db_session, work, chain):
        result = report(db_session, work)

        assert result.tasks == {}
        assert result.work is None

    def test_each_task_is_compared_against_its_own_baseline(self, db_session, work, chain, on):
        first, second = chain
        fix_baseline(db_session, work)
        transition(db_session, first, "start")
        set_progress(db_session, first, 50)

        on(WED)
        result = report(db_session, work)

        # Cimientos was due tonight and is half done; Mampostería starts tomorrow.
        assert (result.tasks[first.id].planned_percent, result.tasks[first.id].gap) == (100, -50)
        assert result.tasks[first.id].standing == "behind"
        assert (result.tasks[second.id].planned_percent, result.tasks[second.id].gap) == (0, 0)
        assert result.tasks[second.id].standing == "on_track"

    def test_the_work_weighs_each_task_by_its_duration(self, db_session, work, chain, on):
        first, _ = chain
        fix_baseline(db_session, work)
        transition(db_session, first, "start")
        set_progress(db_session, first, 50)

        on(WED)
        result = report(db_session, work)

        # Three days at 50 and two at 0, over five; three of five were due.
        assert (result.work.actual_percent, result.work.planned_percent) == (30, 60)
        assert (result.work.gap, result.work.standing) == (-30, "behind")

    def test_a_task_loaded_after_fixing_stays_out_until_it_is_fixed_again(
        self, db_session, world, work, chain, add_task
    ):
        fix_baseline(db_session, work)
        late = add_task(world.project_a, world.firm_a, "Pintura", duration=20)

        result = report(db_session, work)

        assert late not in result.tasks
        # Still out of the five days of the two that were there.
        assert (result.work.actual_percent, result.work.planned_percent) == (0, 20)

        fix_baseline(db_session, work)

        assert late in report(db_session, work).tasks

    def test_recording_progress_does_not_move_the_planned_dates(self, db_session, work, chain, on):
        """ADR-009 section 4: the schedule does not read the progress."""
        first, _ = chain
        fix_baseline(db_session, work)
        transition(db_session, first, "start")
        set_progress(db_session, first, 90)

        fix_baseline(db_session, work)

        assert (first.baseline_start_date, first.baseline_end_date) == (MON, WED)
        assert work.baseline_end_date == FRI
