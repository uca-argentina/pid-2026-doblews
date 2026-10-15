"""The planned progress and the comparison of HU-16, without a database.

services/progress.py is pure on purpose (ADR-009 section 13), so these are
plain function calls. October 2026: the 5th is a Monday, the 9th a Friday.
"""

from datetime import date

import pytest

from app.services.progress import (
    TOLERANCE,
    Comparison,
    Weighted,
    compare,
    planned_percent,
    standing,
    work_progress,
)

MON = date(2026, 10, 5)
TUE = date(2026, 10, 6)
WED = date(2026, 10, 7)
THU = date(2026, 10, 8)
FRI = date(2026, 10, 9)
SAT = date(2026, 10, 10)
SUN = date(2026, 10, 11)
NEXT_MON = date(2026, 10, 12)
NEXT_TUE = date(2026, 10, 13)


# --- What was planned by today ------------------------------------------------


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 10, 2), 0),  # the Friday before it starts
        (MON, 20),  # today counts: the first of five days is done by tonight
        (TUE, 40),
        (WED, 60),
        (THU, 80),
        (FRI, 100),  # the day of the end, like the schedule's inclusive end
        (NEXT_MON, 100),
    ],
)
def test_a_week_long_task_grows_a_fifth_a_day(today, expected):
    assert planned_percent(MON, FRI, today) == expected


def test_a_weekend_in_the_middle_adds_nothing():
    """Thursday to next Tuesday is four working days."""
    assert planned_percent(THU, NEXT_TUE, FRI) == 50
    assert planned_percent(THU, NEXT_TUE, SAT) == 50
    assert planned_percent(THU, NEXT_TUE, SUN) == 50
    assert planned_percent(THU, NEXT_TUE, NEXT_MON) == 75


def test_a_one_day_task_is_due_on_its_day():
    assert planned_percent(WED, WED, TUE) == 0
    assert planned_percent(WED, WED, WED) == 100


def test_a_third_is_rounded_to_the_nearest_whole():
    """Three working days: 33 and 67, not 33 and 66."""
    assert planned_percent(MON, WED, MON) == 33
    assert planned_percent(MON, WED, TUE) == 67


def test_a_baseline_that_starts_on_a_weekend_counts_from_monday():
    """Actual dates are kept as loaded, so a baseline may start on a Saturday."""
    assert planned_percent(SAT, NEXT_TUE, SUN) == 0
    assert planned_percent(SAT, NEXT_TUE, NEXT_MON) == 50


# --- Behind, on track or ahead ------------------------------------------------


@pytest.mark.parametrize(
    ("actual", "planned", "expected"),
    [
        (50, 50, "on_track"),
        (50 - TOLERANCE, 50, "on_track"),  # exactly the tolerance still is
        (50 + TOLERANCE, 50, "on_track"),
        (50 - TOLERANCE - 1, 50, "behind"),
        (50 + TOLERANCE + 1, 50, "ahead"),
        (0, 100, "behind"),
        (100, 0, "ahead"),
    ],
)
def test_the_standing_allows_five_points_either_way(actual, planned, expected):
    assert standing(actual, planned) == expected


def test_the_gap_is_actual_minus_planned():
    assert compare(40, 70) == Comparison(
        actual_percent=40, planned_percent=70, gap=-30, standing="behind"
    )


# --- The whole work -----------------------------------------------------------


def test_each_task_weighs_its_duration():
    """A one-day task done and a nine-day one untouched is a tenth of the work."""
    tasks = [
        Weighted(duration=1, actual_percent=100, planned_percent=100),
        Weighted(duration=9, actual_percent=0, planned_percent=100),
    ]

    assert work_progress(tasks) == Comparison(
        actual_percent=10, planned_percent=100, gap=-90, standing="behind"
    )


def test_the_gap_of_the_work_is_between_the_two_numbers_as_shown():
    """Each side is rounded first: 33 - 67, not the rounding of -33.33."""
    tasks = [
        Weighted(duration=1, actual_percent=100, planned_percent=100),
        Weighted(duration=1, actual_percent=0, planned_percent=100),
        Weighted(duration=1, actual_percent=0, planned_percent=0),
    ]

    assert work_progress(tasks) == Comparison(
        actual_percent=33, planned_percent=67, gap=-34, standing="behind"
    )


def test_a_work_with_nothing_to_compare_has_no_progress():
    """None and not zero: there is no baseline to measure against."""
    assert work_progress([]) is None
