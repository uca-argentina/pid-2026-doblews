"""A work's dashboard over HTTP (HU-19): read only, and only for whoever may see costs.

Nothing is computed here that a section does not already compute. The budget is
build_budget, the same as the budget tab; the original is the work's v1; the
progress, the dates and the tasks' costs are planning_out, the same answer the
planning and progress tabs read. Only the spread by month is new, and it is a
pure function over those same tasks. That is what makes "los números del
dashboard coinciden con los de las secciones de donde salen" true by
construction rather than by care.
"""

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires_any,
)
from app.api.planning_read import CURRENCY, planning_out
from app.core.clock import today
from app.models import BudgetVersion
from app.repositories.budget_version import BudgetVersionRepository
from app.repositories.project import ProjectRepository
from app.schemas.dashboard import (
    BudgetComparisonOut,
    DashboardOut,
    MonthOut,
    OriginalBudgetOut,
    ProgressBlockOut,
    ProjectionOut,
)
from app.services.budget import Budget, build_budget
from app.services.projection import CostSpan, monthly_projection
from app.services.schedule import business_days_between

router = APIRouter(prefix="/firms/{firm_id}/projects/{project_id}/dashboard", tags=["dashboard"])

_ZERO = Decimal("0.00")
_TENTH = Decimal("0.1")


def _compare_budgets(first: BudgetVersion | None, budget: Budget) -> BudgetComparisonOut:
    """The original budget against the live one: difference, percentage, direction.

    D-17: the original is the work's v1 and the updated one is the budget tab's
    total. With no saved budget there is nothing to compare against, and the
    block says to save one.
    """
    if first is None:
        return BudgetComparisonOut(
            original=None,
            updated_total=budget.total,
            prices_as_of=budget.prices_as_of,
            difference=None,
            difference_percent=None,
            direction=None,
        )
    difference = budget.total - first.total
    percent = (
        None
        if first.total == 0
        else (difference * 100 / first.total).quantize(_TENTH, rounding=ROUND_HALF_UP)
    )
    return BudgetComparisonOut(
        original=OriginalBudgetOut(
            version_number=first.version_number,
            note=first.note,
            total=first.total,
            created_at=first.created_at,
        ),
        updated_total=budget.total,
        prices_as_of=budget.prices_as_of,
        difference=difference,
        difference_percent=percent,
        direction="above" if difference > 0 else "below" if difference < 0 else "equal",
    )


@router.get(
    "",
    response_model=DashboardOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.cost.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_dashboard(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> DashboardOut:
    """The three blocks of a work's dashboard, in one answer.

    The guard is the budget's (D-16): the dashboard is about money, so whoever
    may not see costs does not see it — the client of the work gets a 403, and
    the owner comes in through project.view_all like everywhere else. A work
    out of reach, or archived, is a 404 after the guard, as in HU-11.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account.id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    # Money: the original is v1, the updated one the live budget (D-17).
    budget = build_budget(db, firm_id=membership.firm_id, project_id=project.id)
    first = BudgetVersionRepository(db, firm_id=membership.firm_id).first(project.id)
    comparison = _compare_budgets(first, budget)

    # Progress and spending: the planning, exactly as its own tabs read it. The
    # caller may see costs, or the guard would have stopped them.
    planning = planning_out(db, membership, project, sees_cost=True)
    delay = (
        business_days_between(planning.baseline_end_date, planning.planned_end_date)
        if planning.baseline_end_date is not None and planning.planned_end_date is not None
        else None
    )

    # Every dated task counts towards how long the work lasts; only the ones
    # with a cost spend (D-18). The unassigned lines are shown apart.
    months = monthly_projection(
        (
            CostSpan(
                cost=task.cost or _ZERO, start=task.planned_start_date, end=task.planned_end_date
            )
            for task in planning.tasks
            if task.planned_start_date is not None and task.planned_end_date is not None
        ),
        today(),
    )

    return DashboardOut(
        budget=comparison,
        progress=ProgressBlockOut(
            progress=planning.progress,
            project_start_date=planning.project_start_date,
            planned_end_date=planning.planned_end_date,
            baseline_end_date=planning.baseline_end_date,
            end_delay_days=delay,
            has_tasks=bool(planning.tasks),
        ),
        projection=ProjectionOut(
            months=[
                MonthOut(month=month.month, amount=month.amount, is_past=month.is_past)
                for month in months
            ],
            projected_total=sum((month.amount for month in months), start=_ZERO),
            unassigned_cost=planning.unassigned_cost or _ZERO,
        ),
        currency=CURRENCY,
    )
