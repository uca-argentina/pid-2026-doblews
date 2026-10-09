"""Reads a work's planning: the tasks loaded on it (HU-13, ADR-009).
Always inside one firm, from the base repository (ADR-002 section 8), so the
planning screen and its writes never reach another firm's tasks.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Row, Select, func

from app.models import Account, ProjectTask
from app.repositories.base import FirmScopedRepository


@dataclass(frozen=True)
class AssigneeLabel:
    """Who answers for a task, as much of them as the listing renders."""

    account_id: int
    name: str


@dataclass(frozen=True)
class TaskEntry:
    """One task as the planning shows it.

    No cost here. What a task costs comes from the take-off lines assigned to
    it (ProjectRecipeRepository.cost_by_task), and whether the caller may see it
    is a permission, so the route is where the two are put together.
    """

    id: int
    name: str
    description: str | None
    estimated_duration_days: int
    not_before_date: date | None
    status: str
    assignee: AssigneeLabel | None
    actual_start_date: date | None
    actual_end_date: date | None


def _to_entry(row: Row) -> TaskEntry:
    task, assignee_name = row
    return TaskEntry(
        id=task.id,
        name=task.name,
        description=task.description,
        estimated_duration_days=task.estimated_duration_days,
        not_before_date=task.not_before_date,
        status=task.status,
        assignee=(
            None
            if task.assignee_account_id is None
            else AssigneeLabel(account_id=task.assignee_account_id, name=assignee_name)
        ),
        actual_start_date=task.actual_start_date,
        actual_end_date=task.actual_end_date,
    )


class ProjectTaskRepository(FirmScopedRepository[ProjectTask]):
    """Every read starts from the base select, so it is this firm's live tasks only.

    None of these check that the work itself is visible or still active: the
    route resolves the project first and answers 404 before reaching here, the
    same split ProjectRecipeRepository keeps.
    """

    model = ProjectTask

    def _entries(self, project_id: int) -> Select:
        """The live tasks of one work, each with its assignee's name.

        An outer join, because the assignee is optional and a task without one
        must still be listed. Against account and not project_member: a finished
        task keeps its assignee after they leave the team (ADR-009 section 6),
        and their project_member row is gone by then. The name is the person's
        identity, so it is read from where it lives.
        """
        return (
            self.select()
            .where(ProjectTask.project_id == project_id)
            .outerjoin(Account, Account.id == ProjectTask.assignee_account_id)
            .add_columns(Account.name)
        )

    def tasks(self, project_id: int) -> list[TaskEntry]:
        """The tasks of a work, in the order they were loaded.

        By id, so the list does not reshuffle between reloads or when a task is
        renamed. HU-14 is what will give them an order in time.
        """
        rows = self.db.execute(self._entries(project_id).order_by(ProjectTask.id)).all()
        return [_to_entry(row) for row in rows]

    def entry(self, project_id: int, task_id: int) -> TaskEntry | None:
        """One task as the listing renders it. What a write reads back to answer with."""
        row = self.db.execute(self._entries(project_id).where(ProjectTask.id == task_id)).first()
        return None if row is None else _to_entry(row)

    def task(self, project_id: int, task_id: int) -> ProjectTask | None:
        """One task to change, or None.

        None covers "does not exist", "belongs to another work", "belongs to
        another firm" and "already removed" alike. Asking for the project_id as
        well as the task's own id is what stops a PUT on work A's URL from
        editing a task of work B of the same firm, which the firm filter alone
        would allow.
        """
        return self.db.scalars(
            self.select().where(ProjectTask.project_id == project_id, ProjectTask.id == task_id)
        ).first()

    def name_taken(self, project_id: int, name: str, *, exclude_id: int | None = None) -> bool:
        """Is there already a live task of this work under this name?

        Asked before a create or a rename, so the answer is a sentence the
        person can act on rather than uq_project_task_name_active surfacing as a
        500. The index stays as the backstop for two requests landing together.

        Both sides are lowered by the database, the same lower() the index uses:
        lowering one side in Python could disagree with it on an accented letter.

        exclude_id is the task being edited, which must not collide with itself.
        """
        statement = (
            self.select()
            .with_only_columns(ProjectTask.id)
            .where(
                ProjectTask.project_id == project_id,
                func.lower(ProjectTask.name) == func.lower(name),
            )
            .limit(1)
        )
        if exclude_id is not None:
            statement = statement.where(ProjectTask.id != exclude_id)
        return self.db.execute(statement).first() is not None
