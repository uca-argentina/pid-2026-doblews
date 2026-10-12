"""How far along a task should be today, and how that compares with how far it is
(HU-16, ADR-009 section 13).

Pure functions, like services/schedule.py next to it and over its calendar: no
session and no SQL, so every rule here is tested without a database.

Two questions:

- What a task was planned to have done by today, from the dates fixed as its
  baseline. Linear over working days: an even pace is the only one that can be
  assumed without knowing more about the task.
- Whether what was actually recorded is behind that, on track or ahead, for
  one task and for the whole work.

Everything is a whole percentage. The gap is always taken between two numbers
already rounded, so what the screen shows adds up (the criterion of ADR-009
section 8).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from app.services.schedule import business_days_between

Standing = Literal["behind", "on_track", "ahead"]

# How many points the actual progress may differ from the planned one and still
# count as on track. With none, almost no task would ever be: the planned one
# moves every day and the actual one only when someone records it.
TOLERANCE = 5

_DAY = timedelta(days=1)


def _half_up(numerator: int, denominator: int) -> int:
    """numerator / denominator, rounded to the nearest whole, halves upwards.

    In integers, because round() sends a half to the even neighbour: 12.5 would
    become 12 and 13.5 would become 14.
    """
    return (2 * numerator + denominator) // (2 * denominator)


def planned_percent(baseline_start: date, baseline_end: date, today: date) -> int:
    """What a task was planned to have done by the end of today.

    Nothing before its baseline start and everything from its baseline end on.
    In between, the working days gone by — today included, like the inclusive
    end of the schedule — over the working days of the whole stretch.

    The stretch is the baseline's own and not the task's estimated duration,
    which may have been edited since the planning was fixed.
    """
    if today < baseline_start:
        return 0
    if today >= baseline_end:
        return 100
    # business_days_between counts after its first day, so it starts one back.
    before = baseline_start - _DAY
    total = business_days_between(before, baseline_end)
    if total == 0:
        # A baseline that is all weekend: actual dates are kept as loaded, and
        # a task finished over one was fixed with them. It was due at once.
        return 100
    return _half_up(100 * business_days_between(before, today), total)


def standing(actual: int, planned: int) -> Standing:
    """Behind, on track or ahead, by more than the tolerance either way."""
    gap = actual - planned
    if gap < -TOLERANCE:
        return "behind"
    if gap > TOLERANCE:
        return "ahead"
    return "on_track"


@dataclass(frozen=True)
class Comparison:
    """The actual progress against the planned one, of a task or of a work."""

    actual_percent: int
    planned_percent: int
    # Actual minus planned: negative is behind.
    gap: int
    standing: Standing


def compare(actual: int, planned: int) -> Comparison:
    return Comparison(
        actual_percent=actual,
        planned_percent=planned,
        gap=actual - planned,
        standing=standing(actual, planned),
    )


@dataclass(frozen=True)
class Weighted:
    """One task as it counts towards the work: its duration is its weight."""

    duration: int
    actual_percent: int
    planned_percent: int


def work_progress(tasks: Iterable[Weighted]) -> Comparison | None:
    """The progress of a whole work, each task weighing its estimated duration.

    By duration and not by cost (ADR-009 section 13): every task has one, the
    client of the work may see it, and it does not move when prices do.

    The caller passes only the tasks that have a baseline. None when there are
    none: there is nothing to compare, which is not the same as zero.
    """
    tasks = list(tasks)
    total = sum(task.duration for task in tasks)
    if total == 0:
        return None
    actual = _half_up(sum(task.duration * task.actual_percent for task in tasks), total)
    planned = _half_up(sum(task.duration * task.planned_percent for task in tasks), total)
    return compare(actual, planned)
