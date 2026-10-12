"""What the API says about a work's planning, and what it accepts to change it
(HU-13, HU-14, HU-16).
The shapes the planning screen reads and its forms send; the cost fields are
nullable because a caller without project.cost.view gets them empty.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.services.tasks import TaskAction

# The limits of project_task's columns, so a bad value is a 422 naming the field
# rather than a DataError surfacing as a 500.
TaskName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
# Working days. The upper bound is not a rule of the domain: it is forty years
# of them, there so an absurd number is refused here instead of overflowing the
# date arithmetic HU-14 does with it.
Duration = Annotated[int, Field(gt=0, le=10_000)]


class TaskWrite(BaseModel):
    """The add and edit form: the whole editable state of a task.

    One schema for both, like ProjectWrite: the form sends every field every
    time, which is why the edit is a PUT, and null means empty in both
    directions — for the description, the "no antes de" date and the assignee.

    The status and the actual dates are not here. They change through
    TaskTransition and TaskActualDates, never through this form.
    """

    name: TaskName
    description: str | None = None
    estimated_duration_days: Duration
    # "No antes de": a calendar date, not an instant (modelo-datos 3.6).
    not_before_date: date | None = None
    # An account id: the picker is fed by GET .../tasks/assignees.
    assignee_account_id: int | None = None
    # The tasks this one waits for, all of them: the list replaces the ones it
    # had, and an empty one clears them (HU-14).
    predecessor_ids: list[int] = Field(default_factory=list)

    @field_validator("description")
    @classmethod
    def blank_is_no_description(cls, description: str | None) -> str | None:
        # Stored as NULL, so the screen never renders an empty paragraph.
        return (description or "").strip() or None


class TaskTransition(BaseModel):
    """One of the six actions on a task's status, and the day it happened.

    on_date is read only by "start" and "finish", the two that record a date.
    Left out, it is today. Sent with any other action it is refused, by the
    service and with a 409, rather than silently dropped.
    """

    action: TaskAction
    on_date: date | None = None


class TaskActualDates(BaseModel):
    """The correction form for the dates a transition recorded.

    Both are required keys and both may be null: the form sends the pair, and
    which of them a task may carry depends on its status, which the service
    checks.
    """

    actual_start_date: date | None
    actual_end_date: date | None


class TaskProgress(BaseModel):
    """How much of a task is done, as a whole percentage (HU-16).

    The range is the column's CHECK, so a 120 is a 422 naming the field. Whether
    the task is in a status that takes a progress at all is the service's rule.
    """

    progress_percent: Annotated[int, Field(ge=0, le=100)]


class TaskLines(BaseModel):
    """The whole selection of take-off lines of a task. An empty list clears it."""

    line_ids: list[int]


class AssigneeOut(BaseModel):
    """Someone who answers for a task, or who may be picked to."""

    account_id: int
    name: str


class TaskRefOut(BaseModel):
    """Another task, as a dependency names it: enough to say whether it is done."""

    id: int
    name: str
    status: str


class TaskOut(BaseModel):
    """One task, as the planning lists it and a write answers with.

    cost is null when the caller may not see costs. The field stays, so the
    frontend reads one shape and only asks whether the value is there.

    The planned dates, the slack and is_critical are computed on every read
    (ADR-009 section 2) and are null, or false, while the work has no start
    date to plan from. Once a task started, its planned start is its actual
    one, and once it finished so is its end: what happened replaces what was
    planned.
    """

    id: int
    name: str
    description: str | None
    estimated_duration_days: int
    not_before_date: date | None
    status: str
    assignee: AssigneeOut | None
    actual_start_date: date | None
    actual_end_date: date | None
    # How much of it is done, as last recorded: 0 while pending and 100 once
    # finished, whatever was recorded in between (ADR-009 section 13).
    progress_percent: int
    # The take-off lines assigned to it, at today's prices. "0.00" with none.
    cost: Decimal | None
    planned_start_date: date | None
    planned_end_date: date | None
    # Working days it may slip without moving the end of the work. Null once
    # finished: it can no longer be late.
    slack_days: int | None
    # Slack zero: a delay here is a delay of the work.
    is_critical: bool
    # What it waits for and what waits for it, each with its status.
    predecessors: list[TaskRefOut]
    successors: list[TaskRefOut]


class PlanningOut(BaseModel):
    """A work's whole planning in one answer: its tasks and what they add up to.

    One response and not two, so the list and the totals on screen come from the
    same moment.
    """

    # In planned order: by planned start, and by id where that ties or there
    # is no schedule yet.
    tasks: list[TaskOut]
    # What the dates are computed from. Null means the section asks for it.
    project_start_date: date | None
    # The latest planned end among the tasks: when the work is planned to end.
    planned_end_date: date | None
    # What the take-off lines assigned to no task cost.
    unassigned_cost: Decimal | None
    # The sum of the tasks' costs and the unassigned amount, as shown, so the
    # screen adds up exactly. It may differ by cents from the budget's total,
    # which rounds per resource (ADR-009 section 8).
    total_cost: Decimal | None
    currency: str
