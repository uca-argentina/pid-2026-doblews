"""When each task of a work falls, computed from durations and dependencies (HU-14).

The module of ADR-009 section 11: pure functions over tasks and edges already
read from the database. No session and no SQL, so every rule here is tested
without one, and the rest of the application only asks "the dates of this
work" without knowing how they are obtained — which is the seam where a graph
database could replace this one day.

Three parts:

- The calendar: working days, Monday to Friday, no holidays (ADR-009 section
  4). The one calendar HU-16 and HU-19 are meant to share.
- The graph: cycles and topological order.
- The schedule: the forward pass gives each task its planned start and end, the
  backward pass its slack, and the latest end is the work's.

A task of n days that starts on day d occupies d and the n - 1 working days
after it: the end is inclusive. Its successor starts the working day after.
"""

from collections import defaultdict, deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

# The statuses as stored on project_task. Spelled out here rather than imported
# from services/tasks.py, which imports this module.
PENDING = "pending"
FINISHED = "finished"

_DAY = timedelta(days=1)
_SATURDAY = 5


# --- The calendar -----------------------------------------------------------


def is_business_day(day: date) -> bool:
    """Monday to Friday. No holidays: out of scope for the sprint (HU-14)."""
    return day.weekday() < _SATURDAY


def to_business_day(day: date) -> date:
    """The day itself if it is a working day, otherwise the Monday after."""
    while not is_business_day(day):
        day += _DAY
    return day


def back_to_business_day(day: date) -> date:
    """The day itself if it is a working day, otherwise the Friday before."""
    while not is_business_day(day):
        day -= _DAY
    return day


def next_business_day(day: date) -> date:
    """The first working day strictly after this one."""
    return to_business_day(day + _DAY)


def previous_business_day(day: date) -> date:
    """The last working day strictly before this one."""
    return back_to_business_day(day - _DAY)


def add_business_days(start: date, duration: int) -> date:
    """The last day of a task of `duration` working days that starts on `start`.

    A start on a weekend counts from the Monday after, which is when the work
    can actually begin. Whole weeks are jumped at once: a duration may be in
    the thousands (schemas/task.py allows ten thousand).
    """
    if duration < 1:
        raise ValueError("a task lasts at least one working day")
    end = to_business_day(start)
    weeks, days = divmod(duration - 1, 5)
    end += timedelta(weeks=weeks)
    for _ in range(days):
        end = next_business_day(end)
    return end


def subtract_business_days(end: date, duration: int) -> date:
    """The first day of a task of `duration` working days that ends on `end`.

    The inverse of add_business_days. An end on a weekend counts back from the
    Friday before.
    """
    if duration < 1:
        raise ValueError("a task lasts at least one working day")
    start = back_to_business_day(end)
    weeks, days = divmod(duration - 1, 5)
    start -= timedelta(weeks=weeks)
    for _ in range(days):
        start = previous_business_day(start)
    return start


def business_days_between(earlier: date, later: date) -> int:
    """How many working days fall after `earlier` and up to `later`, inclusive.

    Negative when `later` comes first. The slack of a task is this, from its
    planned end to the latest it may end.
    """
    if later < earlier:
        return -business_days_between(later, earlier)
    weeks, days = divmod((later - earlier).days, 7)
    count = weeks * 5
    day = earlier + timedelta(weeks=weeks)
    for _ in range(days):
        day += _DAY
        if is_business_day(day):
            count += 1
    return count


# --- The graph --------------------------------------------------------------

# A dependency, as (predecessor_id, successor_id).
Edge = tuple[int, int]


def _successors(edges: Iterable[Edge]) -> dict[int, list[int]]:
    successors: dict[int, list[int]] = defaultdict(list)
    for predecessor, successor in edges:
        successors[predecessor].append(successor)
    return successors


def find_path(edges: Iterable[Edge], source: int, target: int) -> list[int] | None:
    """A chain of dependencies from `source` to `target`, both included, or None.

    Breadth first, so the chain named in a refusal is the shortest one.
    """
    successors = _successors(edges)
    came_from: dict[int, int | None] = {source: None}
    queue = deque([source])
    while queue:
        current = queue.popleft()
        if current == target:
            path = [current]
            while (previous := came_from[path[-1]]) is not None:
                path.append(previous)
            return path[::-1]
        for following in successors.get(current, []):
            if following not in came_from:
                came_from[following] = current
                queue.append(following)
    return None


def cycle_with_predecessors(
    edges: Iterable[Edge], task_id: int, predecessor_ids: Iterable[int]
) -> list[int] | None:
    """The cycle that giving `task_id` these predecessors would close, or None.

    The graph is acyclic before the change, so any new cycle goes through
    `task_id`: it exists exactly when one of the new predecessors already waits,
    directly or along a longer chain, for `task_id` itself. The edges that
    currently point at `task_id` are being replaced, so they are left out.

    Returned as [task_id, ..., predecessor, task_id], ready to be named.
    """
    kept = [(p, s) for p, s in edges if s != task_id]
    for predecessor in predecessor_ids:
        path = find_path(kept, task_id, predecessor)
        if path is not None:
            return [*path, task_id]
    return None


def topological_order(task_ids: Iterable[int], edges: Iterable[Edge]) -> list[int]:
    """Every task after all of its predecessors. Ties are broken by id.

    Raises ValueError on a cycle. The service never lets one be written, so
    meeting one here is a bug and not something to render.
    """
    ids = sorted(set(task_ids))
    edges = [(p, s) for p, s in edges if p in ids and s in ids]
    successors = _successors(edges)
    waiting = {task_id: 0 for task_id in ids}
    for _, successor in edges:
        waiting[successor] += 1

    ready = deque(task_id for task_id in ids if waiting[task_id] == 0)
    order: list[int] = []
    while ready:
        current = ready.popleft()
        order.append(current)
        for following in sorted(successors.get(current, [])):
            waiting[following] -= 1
            if waiting[following] == 0:
                ready.append(following)

    if len(order) != len(ids):
        raise ValueError("the dependencies of this work form a cycle")
    return order


# --- The schedule -----------------------------------------------------------


@dataclass(frozen=True)
class TaskInput:
    """What the computation needs from a task: what was loaded and what happened."""

    id: int
    duration: int
    status: str
    not_before: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None


@dataclass(frozen=True)
class TaskDates:
    """When a task falls, as computed.

    For a finished task both dates are the actual ones and it has no slack: it
    can no longer be late. For a started one the start is the actual one.
    """

    planned_start: date
    planned_end: date
    # Working days it may slip without moving the end of the work. None once
    # finished.
    slack_days: int | None
    # Slack zero: any delay here delays the work.
    is_critical: bool


@dataclass(frozen=True)
class Schedule:
    tasks: dict[int, TaskDates]
    # The latest planned end among the tasks. None for a work with no tasks.
    project_end: date | None


def compute_schedule(
    project_start: date,
    tasks: Sequence[TaskInput],
    edges: Iterable[Edge],
    today: date,
) -> Schedule:
    """The planned dates, slack and criticality of every task of a work.

    The forward pass is the table of ADR-009 section 4:

    - Finished: its actual dates.
    - In progress or paused: its actual start, and an end that is the later of
      "actual start plus duration" and today. Paused is computed like in
      progress: while it is not finished, it pushes.
    - Pending: the later of the work's start, its "no antes de", the working
      day after its last predecessor ends, and today; plus its duration.

    "Today" is the first working day from today, so on a Saturday nothing is
    planned for the weekend. That floor is what makes nothing planned stay in
    the past: a delay moves everything after it, day by day, without anyone
    recording it.

    The backward pass starts from the end of the work. A task must end the
    working day before the latest start of each successor still pending; a
    successor that already started no longer waits for it (a reopened task,
    ADR-009 section 5), so it does not constrain it. Slack is the working days
    between the planned end and that latest end.

    `edges` may mention tasks outside `tasks`, which are ignored: the caller
    passes only active tasks, and an edge to a removed one is no dependency.
    """
    by_id = {task.id: task for task in tasks}
    edges = [(p, s) for p, s in edges if p in by_id and s in by_id]
    predecessors: dict[int, list[int]] = defaultdict(list)
    for predecessor, successor in edges:
        predecessors[successor].append(predecessor)
    successors = _successors(edges)

    order = topological_order(by_id, edges)
    floor = to_business_day(today)

    start: dict[int, date] = {}
    end: dict[int, date] = {}
    for task_id in order:
        task = by_id[task_id]
        if task.status == FINISHED:
            start[task_id], end[task_id] = task.actual_start, task.actual_end
        elif task.status == PENDING:
            candidates = [project_start, floor]
            if task.not_before is not None:
                candidates.append(task.not_before)
            candidates.extend(next_business_day(end[p]) for p in predecessors[task_id])
            start[task_id] = to_business_day(max(candidates))
            end[task_id] = add_business_days(start[task_id], task.duration)
        else:
            start[task_id] = task.actual_start
            end[task_id] = max(add_business_days(task.actual_start, task.duration), floor)

    if not order:
        return Schedule(tasks={}, project_end=None)
    project_end = max(end.values())

    latest_start: dict[int, date] = {}
    result: dict[int, TaskDates] = {}
    for task_id in reversed(order):
        task = by_id[task_id]
        latest_end = min(
            (
                previous_business_day(latest_start[s])
                for s in successors.get(task_id, [])
                if by_id[s].status == PENDING
            ),
            default=project_end,
        )
        latest_start[task_id] = subtract_business_days(latest_end, task.duration)

        slack = None if task.status == FINISHED else business_days_between(end[task_id], latest_end)
        result[task_id] = TaskDates(
            planned_start=start[task_id],
            planned_end=end[task_id],
            slack_days=slack,
            is_critical=slack == 0,
        )

    return Schedule(tasks=result, project_end=project_end)
