"""What the two routers that write recipes share: support's (HU-8) and a firm's (HU-9).

Both answer a broken catalogue rule with the same status code and a written
recipe with the same shape HU-4's listing uses, so the frontend reads one kind
of error and one kind of recipe whichever screen made the change.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Recipe, RecipeResource, Resource, UnitOfMeasure
from app.schemas.catalog import RecipeLineOut, RecipeOut, UnitRef
from app.schemas.catalog_admin import RecipeWrite
from app.services import catalog_admin
from app.services.catalog_admin import RecipeLineInput

RESOURCE_NOT_FOUND = "Material no encontrado"
RECIPE_NOT_FOUND = "Receta no encontrada"


@contextmanager
def catalog_rules() -> Iterator[None]:
    """Where a broken catalogue rule becomes a status code, for every write.

    422 for a reference the payload got wrong (an inactive or missing unit or
    material — malformed, not a state conflict) and 409 for a rule the
    catalogue's current state refuses (a duplicate name, a material still in
    use). 404 when the id in the URL names nothing active, or nothing the caller
    may reach: a firm's recipe on support's routes, a general or another firm's
    recipe on a firm's.
    """
    try:
        yield
    except catalog_admin.ResourceNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=RESOURCE_NOT_FOUND) from None
    except catalog_admin.RecipeNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=RECIPE_NOT_FOUND) from None
    except catalog_admin.InvalidReferenceError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.detail) from None
    except catalog_admin.CatalogError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def unit_ref(db: Session, unit_of_measure_id: int) -> UnitRef:
    # A primary-key lookup: cheap, and unit_of_measure_id was just validated by
    # the service that wrote the row this is building a response for.
    unit = db.get(UnitOfMeasure, unit_of_measure_id)
    return UnitRef(code=unit.code, abbreviation=unit.abbreviation)


def recipe_out(db: Session, recipe: Recipe) -> RecipeOut:
    """The row a write just produced, lines included, in HU-4's own shape.

    Shaped from the written row rather than by listing the catalogue again, so
    a create or an edit never costs a second full-table query.
    """
    rows = db.execute(
        select(RecipeResource, Resource, UnitOfMeasure.code, UnitOfMeasure.abbreviation)
        .join(Resource, Resource.id == RecipeResource.resource_id)
        .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
        .where(RecipeResource.recipe_id == recipe.id)
        .order_by(Resource.name)
    ).all()
    lines = [
        RecipeLineOut(
            resource_id=line_resource.id,
            name=line_resource.name,
            unit=UnitRef(code=code, abbreviation=abbreviation),
            quantity_per_unit=link.quantity_per_unit,
            reference_price=line_resource.reference_price,
            currency=line_resource.currency,
        )
        for link, line_resource, code, abbreviation in rows
    ]
    return RecipeOut(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        unit=unit_ref(db, recipe.unit_of_measure_id),
        origin="general" if recipe.firm_id is None else "firm",
        lines=lines,
    )


def line_inputs(payload: RecipeWrite) -> list[RecipeLineInput]:
    """The request's lines as the plain values the services take."""
    return [
        RecipeLineInput(resource_id=line.resource_id, quantity_per_unit=line.quantity_per_unit)
        for line in payload.lines
    ]
