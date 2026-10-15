"""Reads a work's take-off: the lines loaded on it and the materials they add up to.
Always inside one firm, from the base repository (ADR-002 section 8), so HU-5's
screen and its writes never reach another firm's lines.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, and_, func

from app.models import (
    ProjectRecipe,
    ProjectTask,
    Recipe,
    RecipeResource,
    Resource,
    UnitOfMeasure,
)
from app.repositories.base import FirmScopedRepository
from app.services.catalog import UnitLabel


@dataclass(frozen=True)
class RecipeLabel:
    """The recipe a line measures, as much of it as the line needs to render."""

    id: int
    name: str
    unit: UnitLabel


@dataclass(frozen=True)
class TaskLabel:
    """The task a line is assigned to, as much of it as the take-off renders."""

    id: int
    name: str


@dataclass(frozen=True)
class TakeoffLineEntry:
    """One line of the take-off: 120 of this recipe, maybe labelled "planta baja"."""

    id: int
    recipe: RecipeLabel
    quantity: Decimal
    note: str | None
    # The task this line is carried out in (HU-13), or None while unassigned.
    task: TaskLabel | None


@dataclass(frozen=True)
class TakeoffMaterialEntry:
    """One resource of the take-off, summed across every line that uses it.

    Named for the materials it only held until T-06, when labour and equipment
    arrived: `type` is what tells the three apart, and HU-11 groups by it.

    cost and unit_price are always computed here. Whether the caller may see them
    is decided at the API, because project.cost.view is a permission and this is
    a read.
    """

    resource_id: int
    name: str
    type: str
    unit: UnitLabel
    quantity: Decimal
    unit_price: Decimal
    cost: Decimal
    currency: str
    price_updated_at: datetime


# How a line reaches its task, in every read here. The is_active half is what
# makes a line that still points at a removed task read as unassigned. The
# service clears task_id when it removes a task (ADR-009 section 7), so this
# should never match anything; it is here so that, if a pointer is ever left
# behind, the line's cost shows up under "sin asignar" instead of vanishing from
# a planning that only lists live tasks.
_LIVE_TASK = and_(ProjectTask.id == ProjectRecipe.task_id, ProjectTask.is_active)


class ProjectRecipeRepository(FirmScopedRepository[ProjectRecipe]):
    """Every read starts from the base select, so it is this firm's live lines only.

    None of these check that the work itself is visible or still active: the
    route resolves the project first and answers 404 before reaching here, the
    same split HU-3 uses between the guard and ProjectRepository.
    """

    model = ProjectRecipe

    def _lines(self, project_id: int) -> Select:
        """The live lines of one work, each with its recipe's name and unit.

        Joins recipe without filtering recipe.is_active: a recipe taken out of
        the catalogue stops being offered for new lines, but the works that
        already use it keep computing it (ADR-005 section 6). Hiding the line
        here would leave its materials in the totals with no line to explain them.

        The task is an outer join: most lines of a work that is not planned yet
        have none, and they are still lines.
        """
        return (
            self.select()
            .where(ProjectRecipe.project_id == project_id)
            .join(Recipe, Recipe.id == ProjectRecipe.recipe_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Recipe.unit_of_measure_id)
            .outerjoin(ProjectTask, _LIVE_TASK)
            .add_columns(
                Recipe.name,
                UnitOfMeasure.code,
                UnitOfMeasure.abbreviation,
                ProjectTask.id,
                ProjectTask.name,
            )
        )

    def lines(self, project_id: int) -> list[TakeoffLineEntry]:
        """The lines of a work, ordered so they do not reshuffle between reloads.

        By recipe first, so two lines of the same wall sit together, then by
        note, which is what tells them apart, then by id for two identical notes.
        """
        rows = self.db.execute(
            self._lines(project_id).order_by(Recipe.name, ProjectRecipe.note, ProjectRecipe.id)
        ).all()
        return [_to_line(row) for row in rows]

    def line_entry(self, project_id: int, line_id: int) -> TakeoffLineEntry | None:
        """One line as the listing renders it. What a write reads back to answer with."""
        row = self.db.execute(self._lines(project_id).where(ProjectRecipe.id == line_id)).first()
        return None if row is None else _to_line(row)

    def line(self, project_id: int, line_id: int) -> ProjectRecipe | None:
        """One line to change, or None.

        None covers "does not exist", "belongs to another work", "belongs to
        another firm" and "already removed" alike. Asking for the project_id as
        well as the line's own id is what stops a PUT on work A's URL from
        editing a line of work B of the same firm, which the firm filter alone
        would allow.
        """
        return self.db.scalars(
            self.select().where(ProjectRecipe.project_id == project_id, ProjectRecipe.id == line_id)
        ).first()

    def materials(self, project_id: int) -> list[TakeoffMaterialEntry]:
        """What the work needs: every resource, with its total quantity and cost.

        Every resource and not only the materials: since T-06 a recipe also
        yields hours of labour and of equipment, and HU-10 asks for them on the
        same screen. Each row carries its `type`, which is what HU-11 groups the
        budget by, and its `unit_price`, the reference price the subtotal of that
        group is built from.

        The query of ADR-003 section 2. Each line is multiplied out by its
        recipe's yields (120 m2 x 60 bricks per m2) and the products are summed
        per material, so two lines of the same wall and two different recipes
        that both take cement all land on the same row.

        Rounded in the database, to 3 decimals for the quantity — the scale the
        take-off is measured in — and to 2 for the cost, which is money. The
        cost is rounded per material, and not per line, so the column on screen
        adds up exactly to the total computed from these same rows.

        Like _lines, it does not filter recipe or resource is_active: the totals
        must agree with the lines shown, and those include retired recipes.

        Grouped by the two primary keys only. Postgres accepts the other columns
        in the select because they depend on those keys, which is what spares
        listing name, price and currency in the GROUP BY.
        """
        taken = ProjectRecipe.quantity * RecipeResource.quantity_per_unit
        statement = (
            self.select()
            .with_only_columns(
                Resource.id,
                Resource.name,
                Resource.type,
                UnitOfMeasure.code,
                UnitOfMeasure.abbreviation,
                func.round(func.sum(taken), 3),
                Resource.reference_price,
                func.round(func.sum(taken * Resource.reference_price), 2),
                Resource.currency,
                Resource.price_updated_at,
            )
            .select_from(ProjectRecipe)
            .join(RecipeResource, RecipeResource.recipe_id == ProjectRecipe.recipe_id)
            .join(Resource, Resource.id == RecipeResource.resource_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
            .where(ProjectRecipe.project_id == project_id)
            .group_by(Resource.id, UnitOfMeasure.id)
            .order_by(Resource.name)
        )
        return [
            TakeoffMaterialEntry(
                resource_id=resource_id,
                name=name,
                type=resource_type,
                unit=UnitLabel(code, abbreviation),
                quantity=quantity,
                unit_price=unit_price,
                cost=cost,
                currency=currency,
                price_updated_at=price_updated_at,
            )
            for (
                resource_id,
                name,
                resource_type,
                code,
                abbreviation,
                quantity,
                unit_price,
                cost,
                currency,
                price_updated_at,
            ) in self.db.execute(statement).all()
        ]

    def cost_by_task(self, project_id: int) -> dict[int | None, Decimal]:
        """What each task of a work costs, and what is left outside every task.

        task id -> cost, with the key None holding the lines assigned to no
        task: the "sin asignar" amount of HU-13.

        The same arithmetic as materials(), on the same rows and at the same
        live prices — each line multiplied out by its recipe's yields and by the
        reference price of each resource (ADR-009 section 8). Only the grouping
        differs: materials() adds the products up per resource, this adds them
        up per task. They are two ways of slicing one take-off.

        Rounded once per task, to 2 decimals, and not per line or per resource,
        so each amount on screen is the rounding of an exact sum. The planning
        total is the sum of these rounded amounts. That is why it may differ by
        cents from the budget total, which rounds per resource instead.

        A task with no lines is not in the answer, and neither is one whose
        lines yield nothing: there is no row to group. Callers read it with
        .get(task_id, 0), which is "una tarea sin líneas cuesta cero".

        Grouped by project_task.id and not by project_recipe.task_id on purpose.
        See _LIVE_TASK: a line pointing at a removed task has no match in the
        outer join, so its key is NULL and it counts as unassigned.
        """
        taken = ProjectRecipe.quantity * RecipeResource.quantity_per_unit
        statement = (
            self.select()
            .with_only_columns(
                ProjectTask.id,
                func.round(func.sum(taken * Resource.reference_price), 2),
            )
            .select_from(ProjectRecipe)
            .join(RecipeResource, RecipeResource.recipe_id == ProjectRecipe.recipe_id)
            .join(Resource, Resource.id == RecipeResource.resource_id)
            .outerjoin(ProjectTask, _LIVE_TASK)
            .where(ProjectRecipe.project_id == project_id)
            .group_by(ProjectTask.id)
        )
        return {task_id: cost for task_id, cost in self.db.execute(statement).all()}


def _to_line(row) -> TakeoffLineEntry:
    line, recipe_name, code, abbreviation, task_id, task_name = row
    return TakeoffLineEntry(
        id=line.id,
        recipe=RecipeLabel(id=line.recipe_id, name=recipe_name, unit=UnitLabel(code, abbreviation)),
        quantity=line.quantity,
        note=line.note,
        task=None if task_id is None else TaskLabel(id=task_id, name=task_name),
    )
