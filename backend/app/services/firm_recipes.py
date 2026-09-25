"""The rules for a firm writing its own recipes (HU-9, ADR-006).

The same rules support follows for the general ones (catalog_admin.py) — a unit
from HU-0's catalogue, at least one line, only active system resources, lines
replaced whole — applied to a recipe that belongs to a firm. Plain functions that
flush and never commit, raising catalog_admin's own exceptions, so the route maps
them to status codes exactly as HU-8's does.

firm_id is always an argument, taken by the route from the resolved membership,
never from the request body.
"""

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeResource
from app.repositories.recipe import FirmRecipeRepository
from app.services.catalog_admin import (
    RECIPE_NEEDS_A_LINE,
    CatalogError,
    RecipeLineInput,
    RecipeNotFoundError,
    insert_recipe_lines,
    name_taken,
    validate_recipe_resources,
    validate_unit_of_measure,
)

# Worded for the architect: the clash is with their own firm's recipes, since
# sharing a general recipe's name is allowed.
FIRM_RECIPE_NAME_TAKEN = "El estudio ya tiene una receta activa con ese nombre"


def get_firm_recipe(db: Session, firm_id: int, recipe_id: int) -> Recipe:
    """This firm's active recipe with this id, for a write to act on.

    A general recipe or another firm's is not found, the same as a missing one
    (ADR-006 rule 2): the route answers 404, never 403.
    """
    recipe = FirmRecipeRepository(db, firm_id=firm_id).get(recipe_id)
    if recipe is None:
        raise RecipeNotFoundError
    return recipe


def _validate(
    db: Session,
    firm_id: int,
    *,
    name: str,
    unit_of_measure_id: int,
    lines: list[RecipeLineInput],
    exclude_id: int | None = None,
) -> None:
    """Every rule a firm's recipe write shares, in the order HU-8 checks them."""
    if not lines:
        raise CatalogError(RECIPE_NEEDS_A_LINE)
    validate_unit_of_measure(db, unit_of_measure_id)
    if name_taken(db, Recipe, name, exclude_id=exclude_id, firm_id=firm_id):
        raise CatalogError(FIRM_RECIPE_NAME_TAKEN)
    validate_recipe_resources(db, {line.resource_id for line in lines})


def create_firm_recipe(
    db: Session,
    firm_id: int,
    *,
    name: str,
    description: str | None,
    unit_of_measure_id: int,
    lines: list[RecipeLineInput],
) -> Recipe:
    """Add a recipe to this firm, header and lines together."""
    _validate(db, firm_id, name=name, unit_of_measure_id=unit_of_measure_id, lines=lines)

    recipe = Recipe(
        firm_id=firm_id,
        name=name,
        description=description,
        unit_of_measure_id=unit_of_measure_id,
    )
    db.add(recipe)
    db.flush()  # assigns the id the lines need

    insert_recipe_lines(db, recipe.id, lines)
    return recipe


def update_firm_recipe(
    db: Session,
    firm_id: int,
    recipe_id: int,
    *,
    name: str,
    description: str | None,
    unit_of_measure_id: int,
    lines: list[RecipeLineInput],
) -> Recipe:
    """Replace one of this firm's recipes, header and every line.

    A take-off already using it recomputes with the new lines, the same as when
    support edits a general recipe: project_recipe points at the recipe, never at
    a copy of it (ADR-003 section 6). Freezing a budget is HU-12's job.
    """
    recipe = get_firm_recipe(db, firm_id, recipe_id)
    _validate(
        db,
        firm_id,
        name=name,
        unit_of_measure_id=unit_of_measure_id,
        lines=lines,
        exclude_id=recipe.id,
    )

    recipe.name = name
    recipe.description = description
    recipe.unit_of_measure_id = unit_of_measure_id

    db.execute(delete(RecipeResource).where(RecipeResource.recipe_id == recipe.id))
    insert_recipe_lines(db, recipe.id, lines)
    return recipe


def deactivate_firm_recipe(db: Session, firm_id: int, recipe_id: int) -> None:
    """Take one of this firm's recipes out of use. A logical removal, no guard.

    Same as a general recipe (ADR-005 section 6): it stops being offered for new
    take-off lines, and the lines that already use it keep computing.
    """
    recipe = get_firm_recipe(db, firm_id, recipe_id)
    recipe.is_active = False
    db.flush()
