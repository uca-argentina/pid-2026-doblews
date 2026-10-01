"""Reads a work's take-off: the lines loaded on it and the materials they add up to.
Always inside one firm, from the base repository (ADR-002 section 8), so HU-5's
screen and its writes never reach another firm's lines.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, func

from app.models import ProjectRecipe, Recipe, RecipeResource, Resource, UnitOfMeasure
from app.repositories.base import FirmScopedRepository
from app.services.catalog import UnitLabel


@dataclass(frozen=True)
class RecipeLabel:
    """The recipe a line measures, as much of it as the line needs to render."""

    id: int
    name: str
    unit: UnitLabel


@dataclass(frozen=True)
class TakeoffLineEntry:
    """One line of the take-off: 120 of this recipe, maybe labelled "planta baja"."""

    id: int
    recipe: RecipeLabel
    quantity: Decimal
    note: str | None


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
        """
        return (
            self.select()
            .where(ProjectRecipe.project_id == project_id)
            .join(Recipe, Recipe.id == ProjectRecipe.recipe_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Recipe.unit_of_measure_id)
            .add_columns(Recipe.name, UnitOfMeasure.code, UnitOfMeasure.abbreviation)
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


def _to_line(row) -> TakeoffLineEntry:
    line, recipe_name, code, abbreviation = row
    return TakeoffLineEntry(
        id=line.id,
        recipe=RecipeLabel(id=line.recipe_id, name=recipe_name, unit=UnitLabel(code, abbreviation)),
        quantity=line.quantity,
        note=line.note,
    )
