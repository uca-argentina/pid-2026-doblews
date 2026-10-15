"""A work's planning over HTTP (HU-13, HU-14, HU-16): its tasks, their status, their
take-off lines, what waits for what, when each falls and how much of it is done.
Where the task permissions guard each endpoint, a work or task out of reach
becomes a 404, and the cost is hidden from whoever may not see it.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    ProjectPermissions,
    requires,
    requires_any,
)
from app.api.planning_read import planning, planning_out
from app.models import Project, ProjectTask
from app.repositories.project import ProjectRepository
from app.repositories.project_task import ProjectTaskRepository
from app.schemas.task import (
    AssigneeOut,
    PlanningOut,
    TaskActualDates,
    TaskLines,
    TaskOut,
    TaskProgress,
    TaskTransition,
    TaskWrite,
)
from app.services.authz import VIEW_ALL
from app.services.tasks import (
    TASK_MANAGE,
    TaskError,
    assign_lines,
    correct_actual_dates,
    create_task,
    fix_baseline,
    list_assignees,
    remove_task,
    set_progress,
    transition,
    update_task,
)

router = APIRouter(prefix="/firms/{firm_id}/projects/{project_id}/tasks", tags=["tasks"])

TASK_NOT_FOUND = "Tarea no encontrada"

COST_VIEW = "project.cost.view"
MANAGE = requires(TASK_MANAGE, "project")


@contextmanager
def _task_rules() -> Iterator[None]:
    """Where a broken rule becomes a 409, for every write here.

    409 and not 422, as in HU-3 and HU-5: the body was well formed, it is the
    state of the work that refuses it — the name is taken, the person left the
    team while the form was open, the task is not in a status that allows it.
    """
    try:
        yield
    except TaskError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _load_project(
    db: Session,
    membership: CurrentMembership,
    account_id: int,
    granted: frozenset[str],
    project_id: int,
) -> Project:
    """The work of the URL, or a 404.

    The guard already proved the caller holds something on this work, but not that
    the work is still active: project permissions resolve from project_member,
    which an archived work keeps. The base select of ProjectRepository filters
    is_active, so an archived work is a 404 here like on its own detail screen.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account_id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


def _tasks(db: Session, membership: CurrentMembership) -> ProjectTaskRepository:
    """The repository, built with the firm the caller has already proved."""
    return ProjectTaskRepository(db, firm_id=membership.firm_id)


def _load_task(
    db: Session, membership: CurrentMembership, project_id: int, task_id: int
) -> ProjectTask:
    """One live task of this work, or a 404. Another work's task is not this work's."""
    task = _tasks(db, membership).task(project_id, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=TASK_NOT_FOUND)
    return task


def _sees_cost(on_project: frozenset[str], granted: frozenset[str]) -> bool:
    """The two heights a cost is visible from, as in the take-off (ADR-003 8).

    project.cost.view is what the client of the work lacks, and project.view_all
    is what lets the owner of the firm see it on a work they are not on.
    """
    return COST_VIEW in on_project or VIEW_ALL in granted


def _read_back(
    db: Session,
    membership: CurrentMembership,
    project: Project,
    task_id: int,
    sees_cost: bool,
) -> TaskOut:
    """The task as stored, with its cost, dates and dependencies, to answer a write.

    Raises rather than 404s: finding nothing right after a successful write is a
    bug, not a task the caller may not see.
    """
    tasks, _, _, _ = planning(db, membership, project, sees_cost)
    for task in tasks:
        if task.id == task_id:
            return task
    raise RuntimeError(f"task {task_id} vanished right after being written")


@router.get(
    "",
    response_model=PlanningOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.task.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_planning(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> PlanningOut:
    """The whole planning of a work: its tasks, what each costs, and what is left out.

    Two ways in, like the take-off: being on the work with project.task.view, or
    owning the firm with project.view_all. Every project role holds the first,
    the client included, who sees what is planned on their work and who does it.

    What the client does not see is what it costs (ADR-009 section 9). Without
    project.cost.view or project.view_all the three cost fields are null, while
    the tasks stay, and so do their dates: when the work is planned to happen
    is no secret from whoever it is for.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    sees_cost = _sees_cost(on_project, granted)

    return planning_out(db, membership, project, sees_cost)


@router.get("/assignees", response_model=list[AssigneeOut], dependencies=[Depends(MANAGE)])
def read_assignees(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> list[AssigneeOut]:
    """Who may be made responsible for a task of this work, for the form's picker.

    Behind manage, like the team's role list: the only screens that need it are
    the ones that assign. And its own endpoint rather than the team listing,
    which asks for project.member.view and would make the frontend repeat the
    rule about who is eligible.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    return [
        AssigneeOut(account_id=person.account_id, name=person.name)
        for person in list_assignees(db, project)
    ]


@router.post("/baseline", response_model=PlanningOut, dependencies=[Depends(MANAGE)])
def fix_planning(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> PlanningOut:
    """Fix the planning: keep today's planned dates as the reference (HU-16).

    A POST with no body: there is nothing to choose, the dates are the ones the
    schedule gives today. Fixing again replaces the previous one. Answers with
    the whole planning and not one task, because every task changed.

    Behind project.task.manage like the rest of the writes here: it is part of
    planning the work, not of editing it.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _task_rules():
        fix_baseline(db, project)
    db.commit()

    return planning_out(db, membership, project, _sees_cost(on_project, granted))


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def create(
    project_id: int,
    payload: TaskWrite,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Load a task onto the work. It is born pending.

    project.task.manage is held by lead and collaborator. The owner's
    project.view_all opens the reading and never the writing: auditing a work is
    not planning it.
    """
    project = _load_project(db, membership, account.id, granted, project_id)

    with _task_rules():
        task = create_task(db, project, **payload.model_dump())
    db.commit()

    return _read_back(db, membership, project, task.id, _sees_cost(on_project, granted))


@router.put("/{task_id}", response_model=TaskOut, dependencies=[Depends(MANAGE)])
def replace(
    project_id: int,
    task_id: int,
    payload: TaskWrite,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Save the edit form of a task: every field of it, every time."""
    project = _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    with _task_rules():
        update_task(db, project, task, **payload.model_dump())
    db.commit()

    return _read_back(db, membership, project, task_id, _sees_cost(on_project, granted))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def delete(
    project_id: int,
    task_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> None:
    """Remove a task. A logical deletion, in any status.

    Its take-off lines go back to unassigned and stay in the take-off. 204 with
    no body: the screen reloads the planning, since the totals move too.
    """
    _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    remove_task(db, task)
    db.commit()


@router.post("/{task_id}/transitions", response_model=TaskOut, dependencies=[Depends(MANAGE)])
def change_status(
    project_id: int,
    task_id: int,
    payload: TaskTransition,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Start, pause, resume, finish or reopen a task, or undo its start.

    A POST of an action and not a PUT of a status: the six actions are the only
    ways a status changes (ADR-009 section 5), and two of them record a date.
    Naming the action is also what makes a double click harmless — the second
    "start" is refused, where a second "status: in_progress" would be accepted
    and would overwrite the date.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    with _task_rules():
        transition(db, task, payload.action, on_date=payload.on_date)
    db.commit()

    return _read_back(db, membership, project, task_id, _sees_cost(on_project, granted))


@router.put("/{task_id}/actual-dates", response_model=TaskOut, dependencies=[Depends(MANAGE)])
def replace_actual_dates(
    project_id: int,
    task_id: int,
    payload: TaskActualDates,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Correct the dates a transition recorded, without changing the status."""
    project = _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    with _task_rules():
        correct_actual_dates(
            db,
            task,
            actual_start_date=payload.actual_start_date,
            actual_end_date=payload.actual_end_date,
        )
    db.commit()

    return _read_back(db, membership, project, task_id, _sees_cost(on_project, granted))


@router.put("/{task_id}/progress", response_model=TaskOut, dependencies=[Depends(MANAGE)])
def replace_progress(
    project_id: int,
    task_id: int,
    payload: TaskProgress,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Record how much of a task is done (HU-16).

    A PUT of the value and not an action: there is no history of it (ADR-009
    section 13), so recording the same number twice changes nothing.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    with _task_rules():
        set_progress(db, task, payload.progress_percent)
    db.commit()

    return _read_back(db, membership, project, task_id, _sees_cost(on_project, granted))


@router.put("/{task_id}/lines", response_model=TaskOut, dependencies=[Depends(MANAGE)])
def replace_lines(
    project_id: int,
    task_id: int,
    payload: TaskLines,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    on_project: ProjectPermissions,
    db: DbSession,
) -> TaskOut:
    """Make these, and only these, the take-off lines of the task.

    Answers with the task, whose cost is what just changed. The lines themselves
    are read from the take-off, where each one says which task it is in.
    """
    project = _load_project(db, membership, account.id, granted, project_id)
    task = _load_task(db, membership, project_id, task_id)

    with _task_rules():
        assign_lines(db, task, payload.line_ids)
    db.commit()

    return _read_back(db, membership, project, task_id, _sees_cost(on_project, granted))
