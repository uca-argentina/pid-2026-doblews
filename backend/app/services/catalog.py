"""Reads over the platform's catalogues (ADR-003).

Units and resources are global to the platform (ADR-003 section 7), so every
caller sees the same rows. Recipes are too, plus the ones a firm wrote for
itself (HU-9, ADR-006): list_recipes is the one read here that takes a firm.
Who may call these is decided by the endpoints, not here.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from app.models import Recipe, RecipeResource, Resource, UnitOfMeasure


@dataclass(frozen=True)
class UnitLabel:
    code: str
    abbreviation: str


@dataclass(frozen=True)
class ResourceEntry:
    """A resource with the label of its unit, ready to render."""

    id: int
    type: str
    name: str
    unit: UnitLabel
    reference_price: Decimal
    currency: str
    price_updated_at: datetime


@dataclass(frozen=True)
class RecipeLine:
    resource_id: int
    name: str
    unit: UnitLabel
    quantity_per_unit: Decimal
    reference_price: Decimal
    currency: str


# Where a recipe comes from, as the screens label it: "General" or "Del estudio".
RecipeOrigin = Literal["general", "firm"]


@dataclass(frozen=True)
class RecipeEntry:
    """A recipe with its lines, which is how HU-4 shows it and HU-5 picks it."""

    id: int
    name: str
    description: str | None
    unit: UnitLabel
    origin: RecipeOrigin
    lines: list[RecipeLine]


def list_units_of_measure(db: Session) -> list[UnitOfMeasure]:
    """The active units of measure, ordered by code."""
    return list(
        db.scalars(
            select(UnitOfMeasure).where(UnitOfMeasure.is_active).order_by(UnitOfMeasure.code)
        )
    )


def list_resources(db: Session) -> list[ResourceEntry]:
    """The active resources, ordered by name, each with its unit's label."""
    rows = db.execute(
        select(Resource, UnitOfMeasure.code, UnitOfMeasure.abbreviation)
        .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
        .where(Resource.is_active)
        .order_by(Resource.name)
    ).all()
    return [
        ResourceEntry(
            id=resource.id,
            type=resource.type,
            name=resource.name,
            unit=UnitLabel(code, abbreviation),
            reference_price=resource.reference_price,
            currency=resource.currency,
            price_updated_at=resource.price_updated_at,
        )
        for resource, code, abbreviation in rows
    ]


def list_recipes(db: Session, *, firm_id: int | None) -> list[RecipeEntry]:
    """The active recipes, ordered by name, each with every line it takes.

    firm_id says whose recipes join the general ones, and it is required so no
    caller gets a scope by omission. None is the system catalogue alone, which
    is what support administers (HU-8). A firm's id adds that firm's own
    recipes and never another's (ADR-006 section 5): OR firm_id = :firm cannot
    match a NULL, nor a row of a different firm.

    Two queries whatever the size of the catalogue — the recipes, then all of
    their lines at once — grouped here by recipe, rather than one query per
    recipe. The models carry no relationship(), so the join is spelled out.

    The lines are not filtered by the resource's is_active: ADR-005 section 6
    refuses to deactivate a resource an active recipe uses, and if one slipped
    through, the take-off would still count it. Hiding it here would make the
    card disagree with the numbers HU-5 computes.
    """
    recipe_unit = aliased(UnitOfMeasure)
    recipes = db.execute(
        select(Recipe, recipe_unit.code, recipe_unit.abbreviation)
        .join(recipe_unit, recipe_unit.id == Recipe.unit_of_measure_id)
        .where(Recipe.is_active, or_(Recipe.firm_id.is_(None), Recipe.firm_id == firm_id))
        .order_by(Recipe.name)
    ).all()
    if not recipes:
        return []

    line_unit = aliased(UnitOfMeasure)
    lines = db.execute(
        select(RecipeResource, Resource, line_unit.code, line_unit.abbreviation)
        .join(Resource, Resource.id == RecipeResource.resource_id)
        .join(line_unit, line_unit.id == Resource.unit_of_measure_id)
        .where(RecipeResource.recipe_id.in_([recipe.id for recipe, _, _ in recipes]))
        .order_by(Resource.name)
    ).all()

    lines_by_recipe: dict[int, list[RecipeLine]] = {}
    for link, resource, code, abbreviation in lines:
        lines_by_recipe.setdefault(link.recipe_id, []).append(
            RecipeLine(
                resource_id=resource.id,
                name=resource.name,
                unit=UnitLabel(code, abbreviation),
                quantity_per_unit=link.quantity_per_unit,
                reference_price=resource.reference_price,
                currency=resource.currency,
            )
        )

    return [
        RecipeEntry(
            id=recipe.id,
            name=recipe.name,
            description=recipe.description,
            unit=UnitLabel(code, abbreviation),
            origin="general" if recipe.firm_id is None else "firm",
            lines=lines_by_recipe.get(recipe.id, []),
        )
        for recipe, code, abbreviation in recipes
    ]
