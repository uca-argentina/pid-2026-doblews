"""Pins who may record a task's progress and what it leaves untouched (HU-16).

Against the session and without HTTP, like test_task_transitions.py. ADR-009
section 13: the status rules the progress, so only a task that started and has
not finished takes one.
"""

from datetime import date

import pytest

from app.models import ProjectTask
from app.services.tasks import (
    PROGRESS_NEEDS_START,
    PROGRESS_OF_FINISHED,
    TaskError,
    set_progress,
)

STARTED = date(2026, 10, 1)
ENDED = date(2026, 10, 5)


@pytest.fixture
def task_in(db_session, world, add_task):
    """A task of firm A's work in the given status, with the dates it implies."""

    def _task(status: str) -> ProjectTask:
        task_id = add_task(
            world.project_a,
            world.firm_a,
            status=status,
            actual_start=None if status == "pending" else STARTED.isoformat(),
            actual_end=ENDED.isoformat() if status == "finished" else None,
        )
        return db_session.get(ProjectTask, task_id)

    return _task


@pytest.mark.parametrize("status", ["in_progress", "paused"])
@pytest.mark.parametrize("percent", [0, 40, 100])
def test_a_started_task_takes_any_progress(db_session, task_in, status, percent):
    task = task_in(status)

    set_progress(db_session, task, percent)

    db_session.refresh(task)
    assert task.progress_percent == percent


def test_a_hundred_does_not_finish_the_task(db_session, task_in):
    task = task_in("in_progress")

    set_progress(db_session, task, 100)

    assert task.status == "in_progress"
    assert task.actual_end_date is None


def test_it_does_not_move_the_actual_dates(db_session, task_in):
    task = task_in("in_progress")

    set_progress(db_session, task, 40)

    assert (task.actual_start_date, task.actual_end_date) == (STARTED, None)


@pytest.mark.parametrize(
    ("status", "refusal", "stays_at"),
    [("pending", PROGRESS_NEEDS_START, 0), ("finished", PROGRESS_OF_FINISHED, 100)],
)
def test_the_status_refuses_it_and_says_what_to_do(db_session, task_in, status, refusal, stays_at):
    task = task_in(status)

    with pytest.raises(TaskError) as refused:
        set_progress(db_session, task, 40)

    assert refused.value.detail == refusal
    assert task.progress_percent == stays_at
