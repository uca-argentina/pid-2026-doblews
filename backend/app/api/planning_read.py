"""Reading a work's planning, shared by every route that shows a piece of it.

The planning tab (HU-13, HU-14), the progress tab (HU-16) and the dashboard
(HU-19) all answer from here, so the costs, dates and progress the dashboard
shows are the very numbers of the sections they come from — computed once, the
same way, rather than re-derived next to each screen.
"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.api.deps import CurrentMembership
from app.models import Project
from app.repositories.project_recipe import ProjectRecipeRepository
from app.repositories.project_task import ProjectTaskRepository, TaskEntry
from app.schemas.task import AssigneeOut, PlanningOut, TaskOut, TaskRefOut, WorkProgressOut
from app.services.progress import Comparison
from app.services.schedule import Schedule
from app.services.tasks import measure_progress, plan_work

# The take-off fixes the currency to ARS (HU-5), and a task's cost is a sum of
# take-off lines, so it cannot differ.
CURRENCY = "ARS"
_ZERO = Decimal("0.00")


def _to_out(
    entry: TaskEntry,
    costs: dict[int | None, Decimal],
    sees_cost: bool,
    schedule: Schedule | None,
    compared: Comparison | None,
    predecessors: list[TaskRefOut],
    successors: list[TaskRefOut],
) -> TaskOut:
    dates = None if schedule is None else schedule.tasks[entry.id]
    return TaskOut(
        id=entry.id,
        name=entry.name,
        description=entry.description,
        estimated_duration_days=entry.estimated_duration_days,
        not_before_date=entry.not_before_date,
        status=entry.status,
        assignee=(
            None
            if entry.assignee is None
            else AssigneeOut(account_id=entry.assignee.account_id, name=entry.assignee.name)
        ),
        actual_start_date=entry.actual_start_date,
        actual_end_date=entry.actual_end_date,
        progress_percent=entry.progress_percent,
        baseline_start_date=entry.baseline_start_date,
        baseline_end_date=entry.baseline_end_date,
        planned_progress_percent=None if compared is None else compared.planned_percent,
        progress_gap=None if compared is None else compared.gap,
        progress_standing=None if compared is None else compared.standing,
        # A task with no lines is absent from the costs: it costs zero.
        cost=costs.get(entry.id, _ZERO) if sees_cost else None,
        planned_start_date=None if dates is None else dates.planned_start,
        planned_end_date=None if dates is None else dates.planned_end,
        slack_days=None if dates is None else dates.slack_days,
        is_critical=False if dates is None else dates.is_critical,
        predecessors=predecessors,
        successors=successors,
    )


def planning(
    db: Session, membership: CurrentMembership, project: Project, sees_cost: bool
) -> tuple[list[TaskOut], Schedule | None, dict[int | None, Decimal], Comparison | None]:
    """Every task of the work as the screen shows it, in planned order, and how
    the work as a whole is doing against its fixed planning.

    The schedule is the whole work's or nothing: a task's dates depend on every
    task before it, so even answering for one task computes them all. A work
    holds tens or a few hundred tasks, which is why ADR-009 section 2 chose to
    recompute on read over storing dates that go stale every midnight.
    """
    tasks = ProjectTaskRepository(db, firm_id=membership.firm_id)
    entries = tasks.tasks(project.id)
    edges = tasks.edges(project.id)
    costs = ProjectRecipeRepository(db, firm_id=membership.firm_id).cost_by_task(project.id)
    schedule = plan_work(project, entries, edges)
    progress = measure_progress(entries)

    refs = {
        entry.id: TaskRefOut(id=entry.id, name=entry.name, status=entry.status) for entry in entries
    }
    predecessors: dict[int, list[TaskRefOut]] = defaultdict(list)
    successors: dict[int, list[TaskRefOut]] = defaultdict(list)
    for predecessor, successor in edges:
        predecessors[successor].append(refs[predecessor])
        successors[predecessor].append(refs[successor])

    out = [
        _to_out(
            entry,
            costs,
            sees_cost,
            schedule,
            progress.tasks.get(entry.id),
            predecessors[entry.id],
            successors[entry.id],
        )
        for entry in entries
    ]
    if schedule is not None:
        out.sort(key=lambda task: (task.planned_start_date, task.planned_end_date, task.id))
    return out, schedule, costs, progress.work


def planning_out(
    db: Session, membership: CurrentMembership, project: Project, sees_cost: bool
) -> PlanningOut:
    """The whole planning in one answer: what the read returns, and what fixing
    the planning answers with, since that changes every task at once."""
    tasks, schedule, costs, progress = planning(db, membership, project, sees_cost)
    unassigned = costs.get(None, _ZERO)

    return PlanningOut(
        tasks=tasks,
        project_start_date=project.estimated_start_date,
        planned_end_date=None if schedule is None else schedule.project_end,
        baseline_set_on=project.baseline_set_on,
        baseline_end_date=project.baseline_end_date,
        progress=(
            None
            if progress is None
            else WorkProgressOut(
                actual_percent=progress.actual_percent,
                planned_percent=progress.planned_percent,
                gap=progress.gap,
                standing=progress.standing,
            )
        ),
        unassigned_cost=unassigned if sees_cost else None,
        # sum() of the amounts as shown, each already rounded, so the screen adds
        # up to exactly this.
        total_cost=(sum((task.cost for task in tasks), start=unassigned) if sees_cost else None),
        currency=CURRENCY,
    )
