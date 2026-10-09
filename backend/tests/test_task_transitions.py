"""Pins how a task's status changes and which actual dates it carries (HU-13).

Against the session and without HTTP, like test_tasks_service.py. Rule 3 of
ADR-009 section 10: only the transitions of section 5 exist. Every pair of
status and action is tried here, the ones that exist and the ones that do not,
so the table in the service cannot gain or lose an arrow unnoticed.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core import clock
from app.models import ProjectTask
from app.services.tasks import (
    DATE_NOT_EXPECTED,
    END_BEFORE_START,
    END_ONLY_WHEN_FINISHED,
    END_REQUIRED,
    FUTURE_DATE,
    PENDING_HAS_NO_DATES,
    START_REQUIRED,
    TRANSITIONS,
    TaskError,
    correct_actual_dates,
    invalid_transition,
    transition,
)

TODAY = date(2026, 10, 9)
STARTED = date(2026, 10, 1)
ENDED = date(2026, 10, 5)

STATUSES = ("pending", "in_progress", "paused", "finished")
ACTIONS = ("start", "pause", "resume", "finish", "reopen", "undo_start")

# The diagram of ADR-009 section 5, typed out again rather than imported: a
# check that reads the same table as the code only proves the table equals itself.
ALLOWED = {
    ("pending", "start"): "in_progress",
    ("in_progress", "pause"): "paused",
    ("paused", "resume"): "in_progress",
    ("in_progress", "finish"): "finished",
    ("finished", "reopen"): "in_progress",
    ("in_progress", "undo_start"): "pending",
}
REFUSED = [
    (status, action) for status in STATUSES for action in ACTIONS if (status, action) not in ALLOWED
]


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch) -> None:
    """Every test here happens on the same day, so "today" is a date to assert."""
    monkeypatch.setattr("app.services.tasks.today", lambda: TODAY)


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


class TestTheTable:
    def test_the_service_holds_exactly_the_documented_transitions(self):
        assert TRANSITIONS == ALLOWED

    @pytest.mark.parametrize(("status", "action"), list(ALLOWED))
    def test_an_allowed_action_leads_to_its_status(self, db_session, task_in, status, action):
        task = task_in(status)

        transition(db_session, task, action)

        assert task.status == ALLOWED[(status, action)]

    @pytest.mark.parametrize(("status", "action"), REFUSED)
    def test_any_other_action_is_refused_and_nothing_changes(
        self, db_session, task_in, status, action
    ):
        task = task_in(status)
        dates = (task.actual_start_date, task.actual_end_date)

        with pytest.raises(TaskError) as refused:
            transition(db_session, task, action)

        assert refused.value.detail == invalid_transition(status, action)
        assert task.status == status
        assert (task.actual_start_date, task.actual_end_date) == dates

    def test_the_refusal_names_the_action_and_the_status(self):
        assert invalid_transition("finished", "pause") == (
            "No se puede pausar una tarea finalizada."
        )
        assert invalid_transition("pending", "undo_start") == (
            "No se puede deshacer el inicio de una tarea pendiente."
        )


class TestTheDatesATransitionRecords:
    def test_starting_records_today_by_default(self, db_session, task_in):
        task = task_in("pending")

        transition(db_session, task, "start")

        assert (task.actual_start_date, task.actual_end_date) == (TODAY, None)

    def test_starting_can_be_given_an_earlier_date(self, db_session, task_in):
        task = task_in("pending")

        transition(db_session, task, "start", on_date=STARTED)

        assert task.actual_start_date == STARTED

    def test_finishing_records_today_by_default(self, db_session, task_in):
        task = task_in("in_progress")

        transition(db_session, task, "finish")

        assert (task.actual_start_date, task.actual_end_date) == (STARTED, TODAY)

    def test_finishing_can_be_given_an_earlier_date(self, db_session, task_in):
        task = task_in("in_progress")

        transition(db_session, task, "finish", on_date=ENDED)

        assert task.actual_end_date == ENDED

    def test_a_task_can_finish_the_day_it_started(self, db_session, task_in):
        task = task_in("in_progress")

        transition(db_session, task, "finish", on_date=STARTED)

        assert task.actual_end_date == STARTED

    def test_pausing_and_resuming_keep_the_start(self, db_session, task_in):
        task = task_in("in_progress")

        transition(db_session, task, "pause")
        transition(db_session, task, "resume")

        assert (task.actual_start_date, task.actual_end_date) == (STARTED, None)

    def test_reopening_forgets_the_end_and_keeps_the_start(self, db_session, task_in):
        task = task_in("finished")

        transition(db_session, task, "reopen")

        assert (task.actual_start_date, task.actual_end_date) == (STARTED, None)

    def test_undoing_the_start_forgets_it(self, db_session, task_in):
        task = task_in("in_progress")

        transition(db_session, task, "undo_start")

        assert (task.actual_start_date, task.actual_end_date) == (None, None)

    def test_starting_in_the_future_is_refused(self, db_session, task_in):
        task = task_in("pending")

        with pytest.raises(TaskError) as refused:
            transition(db_session, task, "start", on_date=TODAY + timedelta(days=1))

        assert refused.value.detail == FUTURE_DATE
        assert task.status == "pending"

    def test_finishing_in_the_future_is_refused(self, db_session, task_in):
        task = task_in("in_progress")

        with pytest.raises(TaskError) as refused:
            transition(db_session, task, "finish", on_date=TODAY + timedelta(days=1))

        assert refused.value.detail == FUTURE_DATE
        assert task.status == "in_progress"

    def test_finishing_before_the_start_is_refused(self, db_session, task_in):
        task = task_in("in_progress")

        with pytest.raises(TaskError) as refused:
            transition(db_session, task, "finish", on_date=STARTED - timedelta(days=1))

        assert refused.value.detail == END_BEFORE_START
        assert (task.status, task.actual_end_date) == ("in_progress", None)

    @pytest.mark.parametrize(
        ("status", "action"),
        [
            ("in_progress", "pause"),
            ("paused", "resume"),
            ("finished", "reopen"),
            ("in_progress", "undo_start"),
        ],
    )
    def test_a_date_on_an_action_that_records_none_is_refused(
        self, db_session, task_in, status, action
    ):
        """Refused rather than ignored, so nobody believes it was recorded."""
        task = task_in(status)

        with pytest.raises(TaskError) as refused:
            transition(db_session, task, action, on_date=STARTED)

        assert refused.value.detail == DATE_NOT_EXPECTED
        assert task.status == status


class TestCorrectingTheDates:
    def test_the_start_of_a_started_task_can_be_moved(self, db_session, task_in):
        task = task_in("in_progress")

        correct_actual_dates(
            db_session, task, actual_start_date=date(2026, 9, 28), actual_end_date=None
        )

        assert (task.status, task.actual_start_date) == ("in_progress", date(2026, 9, 28))

    def test_both_dates_of_a_finished_task_can_be_moved(self, db_session, task_in):
        task = task_in("finished")

        correct_actual_dates(
            db_session, task, actual_start_date=date(2026, 9, 28), actual_end_date=date(2026, 10, 2)
        )

        assert (task.actual_start_date, task.actual_end_date) == (
            date(2026, 9, 28),
            date(2026, 10, 2),
        )

    def test_a_pending_task_takes_no_dates(self, db_session, task_in):
        task = task_in("pending")

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(db_session, task, actual_start_date=STARTED, actual_end_date=None)

        assert refused.value.detail == PENDING_HAS_NO_DATES

    def test_saving_a_pending_task_with_no_dates_changes_nothing(self, db_session, task_in):
        task = task_in("pending")

        correct_actual_dates(db_session, task, actual_start_date=None, actual_end_date=None)

        assert (task.actual_start_date, task.actual_end_date) == (None, None)

    @pytest.mark.parametrize("status", ["in_progress", "paused", "finished"])
    def test_a_started_task_cannot_lose_its_start(self, db_session, task_in, status):
        task = task_in(status)

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(db_session, task, actual_start_date=None, actual_end_date=None)

        assert refused.value.detail == START_REQUIRED
        assert task.actual_start_date == STARTED

    @pytest.mark.parametrize("status", ["in_progress", "paused"])
    def test_an_unfinished_task_takes_no_end(self, db_session, task_in, status):
        task = task_in(status)

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(db_session, task, actual_start_date=STARTED, actual_end_date=ENDED)

        assert refused.value.detail == END_ONLY_WHEN_FINISHED

    def test_a_finished_task_cannot_lose_its_end(self, db_session, task_in):
        task = task_in("finished")

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(db_session, task, actual_start_date=STARTED, actual_end_date=None)

        assert refused.value.detail == END_REQUIRED

    def test_an_end_before_the_start_is_refused(self, db_session, task_in):
        task = task_in("finished")

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(db_session, task, actual_start_date=ENDED, actual_end_date=STARTED)

        assert refused.value.detail == END_BEFORE_START
        assert (task.actual_start_date, task.actual_end_date) == (STARTED, ENDED)

    def test_a_date_in_the_future_is_refused(self, db_session, task_in):
        task = task_in("in_progress")

        with pytest.raises(TaskError) as refused:
            correct_actual_dates(
                db_session, task, actual_start_date=TODAY + timedelta(days=1), actual_end_date=None
            )

        assert refused.value.detail == FUTURE_DATE


class TestTheClock:
    """core/clock.py: "today" is Argentina's, whatever the server's zone is."""

    @pytest.fixture
    def at(self, monkeypatch):
        def _freeze(instant: datetime) -> None:
            class FrozenDatetime(datetime):
                @classmethod
                def now(cls, tz=None):
                    return instant.astimezone(tz)

            monkeypatch.setattr(clock, "datetime", FrozenDatetime)

        return _freeze

    def test_late_evening_in_argentina_is_still_today(self, at):
        """23:30 on the 9th in Buenos Aires is already 02:30 on the 10th in UTC."""
        at(datetime(2026, 10, 10, 2, 30, tzinfo=UTC))

        assert clock.today() == date(2026, 10, 9)

    def test_midday_is_the_same_day_in_both(self, at):
        at(datetime(2026, 10, 9, 15, 0, tzinfo=UTC))

        assert clock.today() == date(2026, 10, 9)
