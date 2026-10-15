"""The monthly projection of HU-19 (D-18), without a database.

services/projection.py is pure, like schedule.py and progress.py. October 2026:
the 1st is a Thursday; the 30th a Friday. November starts on a Sunday.
"""

from datetime import date
from decimal import Decimal

from app.services.projection import CostSpan, monthly_projection

OCT = date(2026, 10, 1)
NOV = date(2026, 11, 1)
DEC = date(2026, 12, 1)
TODAY = date(2026, 10, 12)


def amounts(months) -> dict[date, Decimal]:
    return {month.month: month.amount for month in months}


def test_a_task_inside_one_month_is_spent_in_it():
    months = monthly_projection([CostSpan(Decimal("1000.00"), OCT, date(2026, 10, 9))], TODAY)

    assert amounts(months) == {OCT: Decimal("1000.00")}


def test_a_task_across_two_months_splits_by_working_days():
    # 26/10 to 6/11: Mon 26 to Fri 30 is five working days, and Mon 2 to Fri 6
    # another five.
    span = CostSpan(Decimal("1000.00"), date(2026, 10, 26), date(2026, 11, 6))

    assert amounts(monthly_projection([span], TODAY)) == {
        OCT: Decimal("500.00"),
        NOV: Decimal("500.00"),
    }


def test_the_weekend_does_not_count():
    # Thu 29/10 to Mon 2/11: Thursday and Friday in October, Monday in November.
    span = CostSpan(Decimal("300.00"), date(2026, 10, 29), date(2026, 11, 2))

    assert amounts(monthly_projection([span], TODAY)) == {
        OCT: Decimal("200.00"),
        NOV: Decimal("100.00"),
    }


def test_the_months_of_a_task_add_up_to_exactly_its_cost():
    # One cent over three working days, two in October and one in November:
    # the share that lost the most to rounding gets it.
    span = CostSpan(Decimal("100.01"), date(2026, 10, 29), date(2026, 11, 2))

    months = amounts(monthly_projection([span], TODAY))

    assert sum(months.values()) == Decimal("100.01")
    assert months == {OCT: Decimal("66.67"), NOV: Decimal("33.34")}


def test_months_where_nothing_is_spent_still_show():
    spans = [
        CostSpan(Decimal("100.00"), OCT, date(2026, 10, 2)),
        CostSpan(Decimal("100.00"), date(2026, 12, 1), date(2026, 12, 2)),
    ]

    assert amounts(monthly_projection(spans, TODAY)) == {
        OCT: Decimal("100.00"),
        NOV: Decimal("0.00"),
        DEC: Decimal("100.00"),
    }


def test_a_free_task_still_stretches_the_work():
    spans = [
        CostSpan(Decimal("100.00"), OCT, date(2026, 10, 2)),
        CostSpan(Decimal("0.00"), date(2026, 11, 2), date(2026, 11, 3)),
    ]

    assert amounts(monthly_projection(spans, TODAY)) == {
        OCT: Decimal("100.00"),
        NOV: Decimal("0.00"),
    }


def test_months_before_this_one_are_past():
    spans = [CostSpan(Decimal("100.00"), date(2026, 9, 28), date(2026, 10, 2))]

    months = monthly_projection(spans, TODAY)

    assert [(m.month, m.is_past) for m in months] == [(date(2026, 9, 1), True), (OCT, False)]


def test_a_task_all_on_a_weekend_is_spent_in_the_month_it_ended():
    span = CostSpan(Decimal("50.00"), date(2026, 10, 31), date(2026, 11, 1))

    assert amounts(monthly_projection([span], TODAY)) == {
        OCT: Decimal("0.00"),
        NOV: Decimal("50.00"),
    }


def test_nothing_dated_is_nothing_to_project():
    assert monthly_projection([], TODAY) == []
