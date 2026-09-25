"""The rules for changing the system catalogue: resources and recipes (HU-8).

Plain functions over the session, like roster.py and platform.py: they return
ORM rows, flush and never commit, and a broken rule is one of this module's own
exceptions rather than an HTTPException. The route owns the transaction and the
status codes.

validate_unit_of_measure, validate_recipe_resources, name_taken and
insert_recipe_lines are public because firm_recipes.py (HU-9) applies the very
same rules to a firm's own recipes.

The read side — the shaped listing with unit labels and recipe lines HU-4 and
this module's own screens both show — stays in app.services.catalog. This
module only decides whether a write may happen.

Every recipe this module reaches is a general one (firm_id IS NULL). A firm's
own recipes (HU-9, ADR-006) are that firm's content, and support never reads
or writes a firm's content (ADR-002): to this module they do not exist.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeResource, Resource, UnitOfMeasure

# What support reads when a rule says no. Spanish, because they are rendered as
# they are, and constants so the tests assert against these very strings.
RESOURCE_NAME_TAKEN = "Ya existe un material activo con ese nombre"
RECIPE_NAME_TAKEN = "Ya existe una receta activa con ese nombre"
UNKNOWN_UNIT_OF_MEASURE = "La unidad de medida elegida no existe"
UNKNOWN_RECIPE_RESOURCE = "Un material de las líneas no existe o está dado de baja"
RECIPE_NEEDS_A_LINE = "Una receta activa necesita al menos una línea"


class CatalogError(Exception):
    """A catalogue rule refused the write. Nothing was written.

    Carries the message support reads, so the route passes it through as is.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidReferenceError(Exception):
    """The payload points at a unit of measure or a resource that does not
    qualify: missing, or there but deactivated.

    Kept apart from CatalogError because it is not a conflict with the
    catalogue's current state, it is a malformed reference in an otherwise
    well-formed body — the route answers it with 422, like Pydantic would.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class ResourceNotFoundError(Exception):
    """No active resource with that id.

    Covers a missing id and a deactivated one with the same error: there is no
    reactivation screen (ADR-005 section 6 — loading it again is the path), so
    a deactivated resource is not something a write can reach either.
    """


class RecipeNotFoundError(Exception):
    """No active recipe with that id. Same reasoning as ResourceNotFoundError."""


@dataclass(frozen=True)
class RecipeLineInput:
    """One line of a recipe write, decoupled from the request schema.

    Services take plain values, never Pydantic models — the route is what
    unpacks RecipeWrite.lines into these before calling create_recipe/
    update_recipe.
    """

    resource_id: int
    quantity_per_unit: Decimal


def name_taken(
    db: Session,
    model: type[Resource] | type[Recipe],
    name: str,
    *,
    exclude_id: int | None = None,
    firm_id: int | None = None,
) -> bool:
    """Whether another *active* row of this model already answers to this name.

    Case-insensitive, mirroring the partial unique index each table carries
    (uq_resource_name_active, uq_recipe_name_active_general/_firm): "Cemento"
    and "cemento" are the same name. exclude_id leaves the row itself out, so
    editing a resource without changing its name does not collide with itself.

    A recipe competes only with the recipes of its own origin: the general
    ones when firm_id is None, that firm's otherwise. A firm's recipe may share
    a general recipe's name, or another firm's (ADR-006 section 2).
    """
    stmt = select(model.id).where(model.is_active, func.lower(model.name) == name.lower())
    if model is Recipe:
        stmt = stmt.where(
            Recipe.firm_id.is_(None) if firm_id is None else Recipe.firm_id == firm_id
        )
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    return db.scalar(stmt.limit(1)) is not None


def validate_unit_of_measure(db: Session, unit_of_measure_id: int) -> None:
    """Refuse a unit that is not in HU-0's closed catalogue."""
    found = db.scalar(
        select(UnitOfMeasure.id).where(
            UnitOfMeasure.id == unit_of_measure_id, UnitOfMeasure.is_active
        )
    )
    if found is None:
        raise InvalidReferenceError(UNKNOWN_UNIT_OF_MEASURE)


def validate_recipe_resources(db: Session, resource_ids: set[int]) -> None:
    """Refuse a line pointing at a resource that is missing or deactivated.

    Always the system's resources, for a general recipe and a firm's alike:
    there is no catalogue of materials per firm (HU-9, ADR-006 rule 3).
    """
    found = set(
        db.scalars(select(Resource.id).where(Resource.id.in_(resource_ids), Resource.is_active))
    )
    if resource_ids - found:
        raise InvalidReferenceError(UNKNOWN_RECIPE_RESOURCE)


def insert_recipe_lines(db: Session, recipe_id: int, lines: list[RecipeLineInput]) -> None:
    """Write a recipe's lines. Updating deletes the old set first: the lines are
    replaced whole, never diffed (see update_recipe)."""
    db.add_all(
        RecipeResource(
            recipe_id=recipe_id,
            resource_id=line.resource_id,
            quantity_per_unit=line.quantity_per_unit,
        )
        for line in lines
    )
    db.flush()


def get_resource(db: Session, resource_id: int) -> Resource:
    """The active resource with this id, for a write to act on or answer with."""
    resource = db.get(Resource, resource_id)
    if resource is None or not resource.is_active:
        raise ResourceNotFoundError
    return resource


def get_recipe(db: Session, recipe_id: int) -> Recipe:
    """The active general recipe with this id, for a write to act on or answer with.

    A firm's recipe is not found, the same as a missing one: support must not
    be able to edit it, nor learn that the id exists.
    """
    recipe = db.get(Recipe, recipe_id)
    if recipe is None or not recipe.is_active or recipe.firm_id is not None:
        raise RecipeNotFoundError
    return recipe


def create_resource(
    db: Session, *, name: str, type: str, unit_of_measure_id: int, reference_price: Decimal
) -> Resource:
    """Add a resource to the system catalogue."""
    validate_unit_of_measure(db, unit_of_measure_id)
    if name_taken(db, Resource, name):
        raise CatalogError(RESOURCE_NAME_TAKEN)

    resource = Resource(
        name=name,
        type=type,
        unit_of_measure_id=unit_of_measure_id,
        reference_price=reference_price,
    )
    db.add(resource)
    db.flush()
    return resource


def update_resource(
    db: Session,
    resource_id: int,
    *,
    name: str,
    type: str,
    unit_of_measure_id: int,
    reference_price: Decimal,
) -> Resource:
    """Replace a resource's fields with the ones the edit form sent.

    price_updated_at moves only when reference_price actually changes
    (ADR-005 section 7.3): renaming a material or fixing its unit must not
    make the take-off screen claim its price is fresher than it is.
    """
    resource = get_resource(db, resource_id)
    validate_unit_of_measure(db, unit_of_measure_id)
    if name_taken(db, Resource, name, exclude_id=resource_id):
        raise CatalogError(RESOURCE_NAME_TAKEN)

    if resource.reference_price != reference_price:
        resource.price_updated_at = datetime.now(tz=UTC)

    resource.name = name
    resource.type = type
    resource.unit_of_measure_id = unit_of_measure_id
    resource.reference_price = reference_price
    db.flush()
    return resource


def deactivate_resource(db: Session, resource_id: int) -> None:
    """Take a resource out of the catalogue. A logical removal.

    Refused while any active general recipe still uses it (ADR-005 section 6
    and 7.1): the message names every one of them, so support knows where to
    go remove it first. ix_recipe_resource_resource_id is what keeps this
    check cheap.

    A firm's recipe does not block it and is not named. Support can neither
    see nor edit it, so blocking would leave a resource that can never be
    retired, and naming it would show support a firm's content. That recipe
    keeps computing with the retired resource, and the firm replaces the line
    the next time it saves the recipe, since a write refuses inactive ones.
    """
    resource = get_resource(db, resource_id)

    recipe_names = list(
        db.scalars(
            select(Recipe.name)
            .join(RecipeResource, RecipeResource.recipe_id == Recipe.id)
            .where(
                RecipeResource.resource_id == resource_id,
                Recipe.is_active,
                Recipe.firm_id.is_(None),
            )
            .order_by(Recipe.name)
        )
    )
    if recipe_names:
        raise CatalogError(
            "Este material se usa en estas recetas activas: "
            f"{', '.join(recipe_names)}. Sacalo de ahí antes de darlo de baja."
        )

    resource.is_active = False
    db.flush()


def create_recipe(
    db: Session,
    *,
    name: str,
    description: str | None,
    unit_of_measure_id: int,
    lines: list[RecipeLineInput],
) -> Recipe:
    """Add a recipe, header and lines together, in the caller's transaction.

    RecipeWrite.lines already demands at least one line, but the check is
    repeated here: ADR-005 section 7.2 is explicit that the guarantee belongs
    at the point of saving, not only at the request's edge, since this
    function has its own contract to keep whoever else ends up calling it.
    """
    if not lines:
        raise CatalogError(RECIPE_NEEDS_A_LINE)
    validate_unit_of_measure(db, unit_of_measure_id)
    if name_taken(db, Recipe, name):
        raise CatalogError(RECIPE_NAME_TAKEN)
    validate_recipe_resources(db, {line.resource_id for line in lines})

    recipe = Recipe(name=name, description=description, unit_of_measure_id=unit_of_measure_id)
    db.add(recipe)
    db.flush()  # assigns the id the lines need

    insert_recipe_lines(db, recipe.id, lines)
    return recipe


def update_recipe(
    db: Session,
    recipe_id: int,
    *,
    name: str,
    description: str | None,
    unit_of_measure_id: int,
    lines: list[RecipeLineInput],
) -> Recipe:
    """Replace a recipe's header and every one of its lines.

    The lines are dropped and reinserted rather than diffed: a take-off
    already computed from the old set is unaffected, because project_recipe
    points at the recipe and not at a line (ADR-003 section 2), and the price
    it reads is always the live one (ADR-005 section 5).
    """
    if not lines:
        raise CatalogError(RECIPE_NEEDS_A_LINE)
    recipe = get_recipe(db, recipe_id)
    validate_unit_of_measure(db, unit_of_measure_id)
    if name_taken(db, Recipe, name, exclude_id=recipe_id):
        raise CatalogError(RECIPE_NAME_TAKEN)
    validate_recipe_resources(db, {line.resource_id for line in lines})

    recipe.name = name
    recipe.description = description
    recipe.unit_of_measure_id = unit_of_measure_id

    db.execute(delete(RecipeResource).where(RecipeResource.recipe_id == recipe.id))
    insert_recipe_lines(db, recipe.id, lines)
    return recipe


def deactivate_recipe(db: Session, recipe_id: int) -> None:
    """Take a recipe out of the catalogue. A logical removal, no guard.

    Unlike a resource, a recipe carries no "still in use" check: the works
    that already added it keep computing exactly as before, because their
    project_recipe row points at the recipe and not at its now-hidden listing
    (ADR-005 section 6). Deactivating only stops offering it for new lines.
    """
    recipe = get_recipe(db, recipe_id)
    recipe.is_active = False
    db.flush()
