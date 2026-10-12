"""What the API says about a work's dashboard (HU-19): money, progress and when it
is spent, in one answer. Every number here is read from the same place as the
section it comes from, so the two always agree.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.task import WorkProgressOut


class OriginalBudgetOut(BaseModel):
    """The work's first saved budget, v1 (D-17)."""

    version_number: int
    note: str | None
    total: Decimal
    created_at: datetime


class BudgetComparisonOut(BaseModel):
    """The original budget against the one the take-off adds up to today.

    original is null while the work has no saved budget: the block then says to
    save one. The comparison fields are null with it.
    """

    original: OriginalBudgetOut | None
    # The total of the budget tab, at today's reference prices.
    updated_total: Decimal
    # "Precios de referencia al <fecha>". Null with an empty take-off.
    prices_as_of: datetime | None
    # updated minus original: positive is over, negative is under.
    difference: Decimal | None
    # The difference over the original, one decimal. Null when the original
    # is zero, which has no percentage.
    difference_percent: Decimal | None
    direction: Literal["above", "below", "equal"] | None


class ProgressBlockOut(BaseModel):
    """The whole work's progress against its fixed planning, from HU-16.

    progress is null while there is nothing to compare: no fixed planning, or
    no task with a baseline. The dates are there whenever they exist.
    """

    progress: WorkProgressOut | None
    project_start_date: date | None
    # When it is planned to end today, and when it was when the planning was
    # fixed.
    planned_end_date: date | None
    baseline_end_date: date | None
    # Working days between the two: positive is late. Null without both.
    end_delay_days: int | None
    has_tasks: bool


class MonthOut(BaseModel):
    # The first day of the month.
    month: date
    amount: Decimal
    # Before the month of today.
    is_past: bool


class ProjectionOut(BaseModel):
    """What the work is expected to spend each month (D-18).

    months is empty when there is nothing to project: no start date, or no
    task. projected_total is the sum of the months, which is the sum of the
    tasks' costs; with unassigned_cost it makes the planning's total.
    """

    months: list[MonthOut]
    projected_total: Decimal
    unassigned_cost: Decimal


class DashboardOut(BaseModel):
    budget: BudgetComparisonOut
    progress: ProgressBlockOut
    projection: ProjectionOut
    currency: str
