"""The rules for loading, editing and removing the tasks of a work (HU-13, ADR-009).

Plain functions over the session, like the rest of the services: they return
data and never raise HTTPException. A broken rule is a TaskError, and turning it
into a status code is the API layer's job.

They flush and never commit. The route owns the transaction, which is what lets
"remove the task" and "give its take-off lines back" be one atomic act.

These are the rules of ADR-009 section 10 the schema cannot hold on its own: a
CHECK sees one row, and every one of them needs to look at another table.
"""

from datetime import date
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models import Account, Project, ProjectRecipe, ProjectTask
from app.repositories.project_recipe import ProjectRecipeRepository
from app.repositories.project_task import AssigneeLabel, ProjectTaskRepository
from app.services.authz import project_accounts_granted, project_permissions

# The permission that makes someone eligible to answer for a task. The same one
# every write of the planning demands, so whoever is assigned a task can always
# change its status (ADR-009 section 6).
TASK_MANAGE = "project.task.manage"

PENDING = "pending"
IN_PROGRESS = "in_progress"
PAUSED = "paused"
FINISHED = "finished"

# The six things that can be done to a task's status, and nothing else (HU-13).
# A Literal so the request schema can use it as a field type: an action that is
# not one of these is a 422 from Pydantic before any code here runs.
TaskAction = Literal["start", "pause", "resume", "finish", "reopen", "undo_start"]

# (status, action) -> the status it leads to. The diagram of ADR-009 section 5,
# as data: a pair that is not here is a transition that does not exist.
TRANSITIONS: dict[tuple[str, str], str] = {
    (PENDING, "start"): IN_PROGRESS,
    (IN_PROGRESS, "pause"): PAUSED,
    (PAUSED, "resume"): IN_PROGRESS,
    (IN_PROGRESS, "finish"): FINISHED,
    (FINISHED, "reopen"): IN_PROGRESS,
    (IN_PROGRESS, "undo_start"): PENDING,
}

# The actions that record a date, which is therefore the only ones that take one.
DATED_ACTIONS = ("start", "finish")

# How each action and status reads inside a refusal: "No se puede pausar una
# tarea finalizada."
_ACTION_VERBS = {
    "start": "iniciar",
    "pause": "pausar",
    "resume": "reanudar",
    "finish": "finalizar",
    "reopen": "reabrir",
    "undo_start": "deshacer el inicio de",
}
_STATUS_ADJECTIVES = {
    PENDING: "pendiente",
    IN_PROGRESS: "en curso",
    PAUSED: "pausada",
    FINISHED: "finalizada",
}

# What the architect reads when a rule says no. Spanish, because they are
# rendered as they are, and constants so the tests assert against these very
# strings.
NAME_TAKEN = "Ya hay una tarea con ese nombre en esta obra. Elegí otro."
ASSIGNEE_NOT_ALLOWED = (
    "Esa persona no puede ser responsable de una tarea de esta obra. "
    "Elegí a alguien del equipo que pueda gestionar la planificación."
)
LINE_NOT_AVAILABLE = (
    "Alguna de las líneas elegidas ya no está en el cómputo de esta obra. "
    "Recargá la página y volvé a intentar."
)
TASK_NOT_AVAILABLE = (
    "Esa tarea ya no está en la planificación de esta obra. Recargá la página y elegí otra."
)
DATE_NOT_EXPECTED = "Solo iniciar y finalizar una tarea registran una fecha."
FUTURE_DATE = "Una fecha real no puede ser posterior a hoy."
END_BEFORE_START = "La fecha real de fin no puede ser anterior a la de inicio."
PENDING_HAS_NO_DATES = (
    "Una tarea pendiente no tiene fechas reales. Iniciala para registrar cuándo empezó."
)
START_REQUIRED = "Una tarea que ya empezó necesita su fecha real de inicio."
END_ONLY_WHEN_FINISHED = "Solo una tarea finalizada tiene fecha real de fin."
END_REQUIRED = "Una tarea finalizada necesita su fecha real de fin."


def invalid_transition(status: str, action: str) -> str:
    """The refusal for an action the task's status does not allow."""
    return f"No se puede {_ACTION_VERBS[action]} una tarea {_STATUS_ADJECTIVES[status]}."


class TaskError(Exception):
    """A rule refused the change. Nothing was written.

    Carries the message the architect reads, like TakeoffError does for HU-5.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def list_assignees(db: Session, project: Project) -> list[AssigneeLabel]:
    """Who may be made responsible for a task of this work, for the form's picker.

    Whoever holds project.task.manage on the work: a permission and not a list
    of roles, so moving it between roles in the seed moves this list with it.
    People who left the firm's roster are not offered, because their assignment
    grants nothing while they are out (ADR-002 section 11.3).
    """
    eligible = project_accounts_granted(
        db, project_id=project.id, firm_id=project.firm_id, code=TASK_MANAGE
    )
    rows = db.execute(
        select(Account.id, Account.name)
        .where(Account.id.in_(eligible))
        .order_by(Account.name, Account.id)
    ).all()
    return [AssigneeLabel(account_id=row.id, name=row.name) for row in rows]


def _check_name(db: Session, project: Project, name: str, *, exclude_id: int | None = None) -> None:
    """A task's name is unique among the live tasks of its work (HU-13)."""
    tasks = ProjectTaskRepository(db, firm_id=project.firm_id)
    if tasks.name_taken(project.id, name, exclude_id=exclude_id):
        raise TaskError(NAME_TAKEN)


def _check_assignee(db: Session, project: Project, account_id: int) -> None:
    """May this person be made responsible for a task of this work?

    Rule 4 of ADR-009 section 10: they hold project.task.manage on it, today.
    Someone from another firm, someone not on this team, a viewer, the client
    and someone who left the roster all get the same refusal: for the person at
    the form they are one situation, a picker that offered who it should not.

    Without this, an id from another firm would not be refused by a rule but by
    the composite foreign key against firm_member, and surface as a 500.
    """
    granted = project_permissions(
        db, account_id=account_id, project_id=project.id, firm_id=project.firm_id
    )
    if TASK_MANAGE not in granted:
        raise TaskError(ASSIGNEE_NOT_ALLOWED)


def create_task(
    db: Session,
    project: Project,
    *,
    name: str,
    estimated_duration_days: int,
    description: str | None = None,
    not_before_date: date | None = None,
    assignee_account_id: int | None = None,
) -> ProjectTask:
    """Load a task onto a work. It is born pending, with no actual dates.

    Takes the project rather than an id, like add_line: the route has already
    resolved it through the repository, which is what proved the work is this
    firm's, still active, and visible to the caller.

    firm_id is copied from the project and never taken from the caller, for the
    same reason as in add_line: it is the column the composite foreign keys
    share.
    """
    _check_name(db, project, name)
    if assignee_account_id is not None:
        _check_assignee(db, project, assignee_account_id)

    task = ProjectTask(
        project_id=project.id,
        firm_id=project.firm_id,
        name=name,
        description=description,
        estimated_duration_days=estimated_duration_days,
        not_before_date=not_before_date,
        assignee_account_id=assignee_account_id,
    )
    db.add(task)
    db.flush()  # assigns the id the route reads the task back with
    # Reload what the database filled in: status is a server default.
    db.refresh(task)
    return task


def update_task(
    db: Session,
    project: Project,
    task: ProjectTask,
    *,
    name: str,
    estimated_duration_days: int,
    description: str | None = None,
    not_before_date: date | None = None,
    assignee_account_id: int | None = None,
) -> ProjectTask:
    """Replace what the edit form holds. Every field is written every time.

    The status and the actual dates are not among them: they change through the
    transitions of ADR-009 section 5, never through this form.

    The assignee is checked only when it changes. The rule is about the moment
    of assigning (ADR-009 section 6): someone whose role on the work was lowered
    keeps the tasks they already had, and so does whoever finished a task and
    then left the team. Re-checking an unchanged assignee would refuse to save a
    rename of exactly those tasks.
    """
    _check_name(db, project, name, exclude_id=task.id)
    if assignee_account_id is not None and assignee_account_id != task.assignee_account_id:
        _check_assignee(db, project, assignee_account_id)

    task.name = name
    task.description = description
    task.estimated_duration_days = estimated_duration_days
    task.not_before_date = not_before_date
    task.assignee_account_id = assignee_account_id
    db.flush()
    return task


def remove_task(db: Session, task: ProjectTask) -> ProjectTask:
    """Take a task out of the planning. A logical deletion, in any status.

    Its take-off lines go back to being unassigned, in the same transaction, and
    are never removed themselves (rule 5 of ADR-009 section 10): the work still
    needs that wall, it just is not planned any more. They keep counting in the
    budget and show up under "sin asignar".

    Every line pointing here is cleared, removed ones included, so nothing is
    left referring to a task that no read will ever return.
    """
    task.is_active = False
    db.execute(update(ProjectRecipe).where(ProjectRecipe.task_id == task.id).values(task_id=None))
    db.flush()
    return task


def assign_lines(db: Session, task: ProjectTask, line_ids: list[int]) -> None:
    """Make these, and only these, the take-off lines of a task.

    A replacement and not an addition: the task screen sends the whole selection,
    so a line that was unticked is one that is no longer in it.

    Every id has to be a live line of this same work (rule 7 of ADR-009 section
    10). The composite foreign key already refuses another work's line, but as
    an IntegrityError; and it cannot know about is_active at all.

    A line that belonged to another task is moved here. A line is in one task or
    in none, and the screen shows where each one is before it is picked.
    """
    wanted = set(line_ids)
    lines = ProjectRecipeRepository(db, firm_id=task.firm_id)
    of_this_work = lines.select().where(ProjectRecipe.project_id == task.project_id)

    chosen = db.scalars(of_this_work.where(ProjectRecipe.id.in_(wanted))).all()
    if len(chosen) != len(wanted):
        raise TaskError(LINE_NOT_AVAILABLE)

    for line in db.scalars(of_this_work.where(ProjectRecipe.task_id == task.id)).all():
        if line.id not in wanted:
            line.task_id = None
    for line in chosen:
        line.task_id = task.id
    db.flush()


def set_line_task(db: Session, line: ProjectRecipe, task: ProjectTask | None) -> ProjectRecipe:
    """Assign one take-off line to a task, or to none. The take-off screen's side.

    Takes the line and the task already loaded, like update_line: the route got
    both through their repositories asking for this work's id, which is what
    proved each is live and belongs to it.
    """
    line.task_id = None if task is None else task.id
    db.flush()
    return line


def unassign_open_tasks(db: Session, *, project_id: int, account_id: int) -> None:
    """Leave without assignee the unfinished tasks of someone leaving a work's team.

    Rule 6 of ADR-009 section 10. The finished ones keep them: that is the
    record of who did the work, and the reason the column points at firm_member
    rather than at project_member, which is really deleted.

    Called from the places that delete a project_member row, in their
    transaction, so nobody is ever off the team and still answering for a task.
    """
    db.execute(
        update(ProjectTask)
        .where(
            ProjectTask.project_id == project_id,
            ProjectTask.assignee_account_id == account_id,
            ProjectTask.status != FINISHED,
        )
        .values(assignee_account_id=None)
    )


def _check_actual_dates(start: date | None, end: date | None) -> None:
    """What holds for any pair of actual dates, whatever the status.

    Neither is in the future: an actual date is something that happened. And the
    end is not before the start, which the schema also refuses, but as a CHECK
    violation the person would read as a 500.

    "The future" is measured in Argentina and not on the server (core/clock.py).
    """
    current = today()
    if any(value is not None and value > current for value in (start, end)):
        raise TaskError(FUTURE_DATE)
    if start is not None and end is not None and end < start:
        raise TaskError(END_BEFORE_START)


def transition(
    db: Session, task: ProjectTask, action: TaskAction, *, on_date: date | None = None
) -> ProjectTask:
    """Change a task's status by one of the six actions of HU-13.

    Rule 3 of ADR-009 section 10: only the transitions of section 5 exist.
    Anything else is refused with a sentence naming the action and the status,
    which is also what a double click gets — the second "iniciar" finds the task
    already in progress.

    Starting records the actual start and finishing the actual end: on_date, or
    today when it is left out. The other four take no date, and sending one is
    refused rather than ignored, so a caller cannot believe it was recorded.
    Reopening forgets the end and undoing the start forgets the start, which is
    what keeps the row inside the CHECKs that tie the dates to the status.

    HU-14 adds one more refusal to "start": a task cannot start while one of its
    predecessors is unfinished (rule 2). It belongs right where the comment
    below is, and nowhere else changes.
    """
    target = TRANSITIONS.get((task.status, action))
    if target is None:
        raise TaskError(invalid_transition(task.status, action))
    if on_date is not None and action not in DATED_ACTIONS:
        raise TaskError(DATE_NOT_EXPECTED)

    if action == "start":
        # HU-14: refuse here if any active predecessor is not finished.
        started = on_date or today()
        _check_actual_dates(started, None)
        task.actual_start_date = started
    elif action == "finish":
        finished = on_date or today()
        _check_actual_dates(task.actual_start_date, finished)
        task.actual_end_date = finished
    elif action == "reopen":
        task.actual_end_date = None
    elif action == "undo_start":
        task.actual_start_date = None

    task.status = target
    db.flush()
    return task


def correct_actual_dates(
    db: Session,
    task: ProjectTask,
    *,
    actual_start_date: date | None,
    actual_end_date: date | None,
) -> ProjectTask:
    """Fix the dates a transition recorded, without changing the status.

    HU-13: "por defecto hoy, y se pueden corregir". The task was started last
    Thursday and nobody pressed the button until Monday.

    Both dates are sent every time, like every form here, and which ones a task
    may carry is decided by its status: none while pending, the start once it
    began, and both only when finished. Those are the same four CHECKs of the
    schema, said first and in words.
    """
    if task.status == PENDING:
        if actual_start_date is not None or actual_end_date is not None:
            raise TaskError(PENDING_HAS_NO_DATES)
    else:
        if actual_start_date is None:
            raise TaskError(START_REQUIRED)
        if task.status == FINISHED and actual_end_date is None:
            raise TaskError(END_REQUIRED)
        if task.status != FINISHED and actual_end_date is not None:
            raise TaskError(END_ONLY_WHEN_FINISHED)
    _check_actual_dates(actual_start_date, actual_end_date)

    task.actual_start_date = actual_start_date
    task.actual_end_date = actual_end_date
    db.flush()
    return task
