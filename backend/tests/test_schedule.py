"""The calendar, the graph and the schedule of HU-14, without a database.

services/schedule.py is pure on purpose (ADR-009 section 11), so these are
plain function calls. October 2026: the 5th is a Monday, the 9th a Friday.
"""

from datetime import date

import pytest

from app.services.schedule import (
    TaskInput,
    add_business_days,
    business_days_between,
    compute_schedule,
    cycle_with_predecessors,
    next_business_day,
    subtract_business_days,
    to_business_day,
    topological_order,
)

MON = date(2026, 10, 5)
FRI = date(2026, 10, 9)
SAT = date(2026, 10, 10)
NEXT_MON = date(2026, 10, 12)
# Far enough back that "today" never pushes anything in these tests.
LONG_AGO = date(2026, 1, 1)


def pending(task_id: int, duration: int, **kwargs) -> TaskInput:
    return TaskInput(id=task_id, duration=duration, status="pending", **kwargs)


# --- The calendar -----------------------------------------------------------


def test_a_weekend_day_rolls_to_monday():
    assert to_business_day(SAT) == NEXT_MON
    assert to_business_day(FRI) == FRI


def test_the_day_after_friday_is_monday():
    assert next_business_day(FRI) == NEXT_MON


@pytest.mark.parametrize(
    ("start", "duration", "end"),
    [
        (MON, 1, MON),
        (MON, 5, FRI),
        (MON, 6, NEXT_MON),
        (date(2026, 10, 8), 3, NEXT_MON),  # Thursday, Friday, Monday
        (SAT, 1, NEXT_MON),
        (MON, 11, date(2026, 10, 19)),
    ],
)
def test_adding_working_days_skips_weekends(start, duration, end):
    assert add_business_days(start, duration) == end


def test_subtracting_is_the_inverse_of_adding():
    for duration in (1, 2, 5, 6, 13, 40):
        end = add_business_days(MON, duration)
        assert subtract_business_days(end, duration) == MON


def test_working_days_between_skips_the_weekend():
    assert business_days_between(FRI, NEXT_MON) == 1
    assert business_days_between(MON, FRI) == 4
    assert business_days_between(MON, MON) == 0
    assert business_days_between(NEXT_MON, FRI) == -1


# --- The graph --------------------------------------------------------------


def test_topological_order_puts_predecessors_first():
    assert topological_order([3, 2, 1], [(3, 1), (1, 2)]) == [3, 1, 2]


def test_topological_order_refuses_a_cycle():
    with pytest.raises(ValueError):
        topological_order([1, 2], [(1, 2), (2, 1)])


def test_a_direct_cycle_is_found():
    # 1 -> 2 exists; making 1 wait for 2 closes it.
    assert cycle_with_predecessors([(1, 2)], 1, [2]) == [1, 2, 1]


def test_a_longer_cycle_is_found():
    assert cycle_with_predecessors([(1, 2), (2, 3)], 1, [3]) == [1, 2, 3, 1]


def test_replacing_the_predecessors_does_not_count_the_old_ones():
    # 2 waits for 1 today. Giving 2 a new predecessor 3 drops (1, 2): no cycle.
    assert cycle_with_predecessors([(1, 2), (2, 3)], 2, []) is None
    assert cycle_with_predecessors([(1, 2)], 2, [1]) is None


# --- The schedule -----------------------------------------------------------


def test_a_task_without_predecessors_starts_with_the_work():
    schedule = compute_schedule(MON, [pending(1, 3)], [], LONG_AGO)
    dates = schedule.tasks[1]
    assert (dates.planned_start, dates.planned_end) == (MON, date(2026, 10, 7))
    assert schedule.project_end == date(2026, 10, 7)


def test_a_work_starting_on_a_weekend_starts_on_monday():
    schedule = compute_schedule(SAT, [pending(1, 1)], [], LONG_AGO)
    assert schedule.tasks[1].planned_start == NEXT_MON


def test_not_before_delays_the_start_only_when_later():
    later = date(2026, 10, 7)
    schedule = compute_schedule(
        MON,
        [pending(1, 1, not_before=later), pending(2, 1, not_before=LONG_AGO)],
        [],
        LONG_AGO,
    )
    assert schedule.tasks[1].planned_start == later
    assert schedule.tasks[2].planned_start == MON


def test_a_chain_starts_the_working_day_after_its_predecessor():
    # A (5 days) ends Friday, B starts Monday.
    schedule = compute_schedule(MON, [pending(1, 5), pending(2, 2)], [(1, 2)], LONG_AGO)
    assert schedule.tasks[2].planned_start == NEXT_MON
    assert schedule.tasks[2].planned_end == date(2026, 10, 13)


def test_a_task_waits_for_its_latest_predecessor():
    # 1 (1 day) and 2 (3 days) both precede 3.
    schedule = compute_schedule(
        MON, [pending(1, 1), pending(2, 3), pending(3, 1)], [(1, 3), (2, 3)], LONG_AGO
    )
    assert schedule.tasks[3].planned_start == date(2026, 10, 8)


def test_slack_and_critical_path():
    # 1 (3) -> 2 (2) is the long branch; 3 (1) is alone.
    schedule = compute_schedule(
        MON, [pending(1, 3), pending(2, 2), pending(3, 1)], [(1, 2)], LONG_AGO
    )
    assert schedule.project_end == FRI
    assert schedule.tasks[1].slack_days == 0 and schedule.tasks[1].is_critical
    assert schedule.tasks[2].slack_days == 0 and schedule.tasks[2].is_critical
    assert schedule.tasks[3].slack_days == 4 and not schedule.tasks[3].is_critical


def test_a_diamond_gives_slack_to_the_short_branch():
    # 1 -> {2 (5), 3 (1)} -> 4
    tasks = [pending(1, 1), pending(2, 5), pending(3, 1), pending(4, 1)]
    edges = [(1, 2), (1, 3), (2, 4), (3, 4)]
    schedule = compute_schedule(MON, tasks, edges, LONG_AGO)
    assert schedule.tasks[3].slack_days == 4
    assert all(schedule.tasks[t].is_critical for t in (1, 2, 4))


def test_actual_dates_replace_planned_ones():
    finished = TaskInput(
        id=1, duration=5, status="finished", actual_start=MON, actual_end=date(2026, 10, 6)
    )
    schedule = compute_schedule(MON, [finished, pending(2, 1)], [(1, 2)], LONG_AGO)
    assert schedule.tasks[1].planned_end == date(2026, 10, 6)
    assert schedule.tasks[1].slack_days is None and not schedule.tasks[1].is_critical
    # The successor follows what happened, not what was planned.
    assert schedule.tasks[2].planned_start == date(2026, 10, 7)


def test_an_overdue_task_in_progress_ends_no_earlier_than_today():
    today = date(2026, 10, 14)
    started = TaskInput(id=1, duration=2, status="in_progress", actual_start=MON)
    schedule = compute_schedule(MON, [started, pending(2, 1)], [(1, 2)], today)
    assert schedule.tasks[1].planned_start == MON
    assert schedule.tasks[1].planned_end == today
    assert schedule.tasks[2].planned_start == date(2026, 10, 15)


def test_paused_pushes_like_in_progress():
    today = date(2026, 10, 14)
    paused = TaskInput(id=1, duration=2, status="paused", actual_start=MON)
    schedule = compute_schedule(MON, [paused], [], today)
    assert schedule.tasks[1].planned_end == today


def test_an_overdue_pending_task_starts_today():
    today = date(2026, 10, 14)
    schedule = compute_schedule(MON, [pending(1, 1), pending(2, 1)], [(1, 2)], today)
    assert schedule.tasks[1].planned_start == today
    assert schedule.tasks[2].planned_start == date(2026, 10, 15)


def test_nothing_is_planned_for_a_weekend_today():
    schedule = compute_schedule(MON, [pending(1, 1)], [], SAT)
    assert schedule.tasks[1].planned_start == NEXT_MON


def test_a_started_successor_does_not_constrain_a_reopened_predecessor():
    # 1 was reopened after 2 started. 2 no longer waits for 1, so 1's slack
    # comes from the end of the work.
    reopened = TaskInput(id=1, duration=1, status="in_progress", actual_start=MON)
    started = TaskInput(id=2, duration=10, status="in_progress", actual_start=MON)
    schedule = compute_schedule(MON, [reopened, started], [(1, 2)], MON)
    assert schedule.tasks[1].slack_days == 9


def test_edges_to_tasks_not_passed_are_ignored():
    schedule = compute_schedule(MON, [pending(2, 1)], [(1, 2)], LONG_AGO)
    assert schedule.tasks[2].planned_start == MON


def test_a_work_without_tasks_has_no_end():
    assert compute_schedule(MON, [], [], LONG_AGO).project_end is None
