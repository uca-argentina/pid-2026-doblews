"""How much a work is expected to spend in each month of it (HU-19, D-18).

Pure functions, like services/schedule.py and services/progress.py next to it,
and over the same calendar: no session and no SQL, so every rule here is tested
without a database.

Each task spends its cost evenly over its working days, so a month gets the
share of the task's working days that fall in it. The same even pace HU-16
assumes for the planned progress, and for the same reason: it is the only one
that can be assumed without knowing more about the task.

The take-off lines assigned to no task are not spread here: nobody planned
when they are spent, and the caller shows them apart.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.services.schedule import business_days_between

_DAY = timedelta(days=1)
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class CostSpan:
    """One task as the projection sees it: what it costs and when it happens."""

    cost: Decimal
    start: date
    end: date


@dataclass(frozen=True)
class MonthAmount:
    # The first day of the month, which is how a month travels as a date.
    month: date
    amount: Decimal
    # Before the month of today: already gone by, shown dimmed.
    is_past: bool


def _first_of(day: date) -> date:
    return day.replace(day=1)


def _next_month(month: date) -> date:
    return (month.replace(day=28) + timedelta(days=4)).replace(day=1)


def _months(start: date, end: date) -> list[date]:
    """Every month from the one of `start` to the one of `end`, both included."""
    months, month = [], _first_of(start)
    while month <= end:
        months.append(month)
        month = _next_month(month)
    return months


def _working_days(start: date, end: date) -> int:
    """Working days from `start` to `end`, both included."""
    return business_days_between(start - _DAY, end)


def _spread(span: CostSpan) -> dict[date, Decimal]:
    """A task's cost over the months it spans, by its working days in each.

    In whole cents, with the largest-remainder method: every month gets its
    share rounded down, and the cents left over go to the months that lost the
    most to the rounding. So the months of a task always add up to exactly its
    cost — the total of the chart is the sum of the costs the planning shows.

    A task with no working day at all (actual dates loaded over a weekend) is
    spent in the month it ended.
    """
    months = _months(span.start, span.end)
    days = {
        month: _working_days(max(span.start, month), min(span.end, _next_month(month) - _DAY))
        for month in months
    }
    total = sum(days.values())
    cents = int((span.cost / _CENT).to_integral_value())
    if total == 0:
        return {_first_of(span.end): span.cost}

    shares = {month: cents * days[month] // total for month in months}
    left = cents - sum(shares.values())
    # Ties go to the earlier month: the order is the calendar's, never random.
    by_remainder = sorted(months, key=lambda month: (-(cents * days[month] % total), month))
    for month in by_remainder[:left]:
        shares[month] += 1
    return {month: Decimal(share) * _CENT for month, share in shares.items()}


def monthly_projection(spans: Iterable[CostSpan], today: date) -> list[MonthAmount]:
    """What is expected to be spent in each month of the work.

    Every month from the earliest start to the latest end, the ones where
    nothing is spent included, so the chart has no gaps. A task that costs
    nothing still counts towards how long the work lasts. Empty when there is
    nothing dated to project.
    """
    spans = list(spans)
    if not spans:
        return []

    amounts: dict[date, Decimal] = defaultdict(Decimal)
    for span in spans:
        if span.cost > 0:
            for month, amount in _spread(span).items():
                amounts[month] += amount

    current = _first_of(today)
    return [
        MonthAmount(
            month=month,
            amount=amounts.get(month, Decimal("0")).quantize(_CENT),
            is_past=month < current,
        )
        for month in _months(min(s.start for s in spans), max(s.end for s in spans))
    ]
