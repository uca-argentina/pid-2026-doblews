"""Support's catalogue admin screens: resources and recipes (HU-8, ADR-005).

Under /platform/catalog and never under /firms/{firm_id}: the catalogue belongs
to no firm, and support belongs to no roster (same reasoning as platform.py for
HU-7). Every route here demands catalog.manage in platform scope, which is what
keeps this out of every firm's reach — an owner or an architect gets 403.

The read side reuses app.services.catalog as is: GET here returns exactly what
HU-4's screens show everyone else, because it is the same catalogue. Only the
write responses are shaped locally, from the row catalog_admin.py just wrote,
so a create or an edit never costs a second full-table query.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, requires
from app.models import Recipe, RecipeResource, Resource, UnitOfMeasure
from app.schemas.catalog import RecipeLineOut, RecipeOut, ResourceOut, UnitRef
from app.schemas.catalog_admin import RecipeWrite, ResourceWrite
from app.services import catalog, catalog_admin
from app.services.catalog_admin import RecipeLineInput

router = APIRouter(prefix="/platform/catalog", tags=["catalog-admin"])

RESOURCE_NOT_FOUND = "Material no encontrado"
RECIPE_NOT_FOUND = "Receta no encontrada"


@contextmanager
def _catalog_rules() -> Iterator[None]:
    """Where a broken catalogue rule becomes a status code, for every write here.

    422 for a reference the payload got wrong (an inactive or missing unit or
    material — malformed, not a state conflict) and 409 for a rule the
    catalogue's current state refuses (a duplicate name, a material still in
    use). 404 when the id in the URL names nothing active.
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


def _unit_ref(db: DbSession, unit_of_measure_id: int) -> UnitRef:
    # A primary-key lookup: cheap, and unit_of_measure_id was just validated by
    # the service that wrote the row this is building a response for.
    unit = db.get(UnitOfMeasure, unit_of_measure_id)
    return UnitRef(code=unit.code, abbreviation=unit.abbreviation)


def _resource_out(db: DbSession, resource: Resource) -> ResourceOut:
    """The row a write just produced, in the same shape HU-4's listing uses."""
    return ResourceOut(
        id=resource.id,
        type=resource.type,
        name=resource.name,
        unit=_unit_ref(db, resource.unit_of_measure_id),
        reference_price=resource.reference_price,
        currency=resource.currency,
        price_updated_at=resource.price_updated_at,
    )


def _recipe_out(db: DbSession, recipe: Recipe) -> RecipeOut:
    """The row a write just produced, lines included, in HU-4's own shape."""
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
        unit=_unit_ref(db, recipe.unit_of_measure_id),
        lines=lines,
    )


def _line_inputs(payload: RecipeWrite) -> list[RecipeLineInput]:
    return [
        RecipeLineInput(resource_id=line.resource_id, quantity_per_unit=line.quantity_per_unit)
        for line in payload.lines
    ]


@router.get(
    "/resources",
    response_model=list[ResourceOut],
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def list_catalog_resources(db: DbSession) -> list[ResourceOut]:
    """Every active resource, the same listing HU-4 shows everyone else."""
    return [
        ResourceOut.model_validate(entry, from_attributes=True)
        for entry in catalog.list_resources(db)
    ]


@router.post(
    "/resources",
    response_model=ResourceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def create_catalog_resource(payload: ResourceWrite, db: DbSession) -> ResourceOut:
    with _catalog_rules():
        resource = catalog_admin.create_resource(
            db,
            name=payload.name,
            type=payload.type,
            unit_of_measure_id=payload.unit_of_measure_id,
            reference_price=payload.reference_price,
        )
    db.commit()
    return _resource_out(db, resource)


@router.put(
    "/resources/{resource_id}",
    response_model=ResourceOut,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def update_catalog_resource(resource_id: int, payload: ResourceWrite, db: DbSession) -> ResourceOut:
    with _catalog_rules():
        resource = catalog_admin.update_resource(
            db,
            resource_id,
            name=payload.name,
            type=payload.type,
            unit_of_measure_id=payload.unit_of_measure_id,
            reference_price=payload.reference_price,
        )
    db.commit()
    return _resource_out(db, resource)


@router.delete(
    "/resources/{resource_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def deactivate_catalog_resource(resource_id: int, db: DbSession) -> None:
    """Take a resource out of the catalogue. 204: the frontend already has the row.

    Refused with 409 while an active recipe still uses it (ADR-005 section 6),
    naming which ones.
    """
    with _catalog_rules():
        catalog_admin.deactivate_resource(db, resource_id)
    db.commit()


@router.get(
    "/recipes",
    response_model=list[RecipeOut],
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def list_catalog_recipes(db: DbSession) -> list[RecipeOut]:
    """Every active recipe with its lines, the same listing HU-4 shows everyone else."""
    return [
        RecipeOut.model_validate(entry, from_attributes=True) for entry in catalog.list_recipes(db)
    ]


@router.post(
    "/recipes",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def create_catalog_recipe(payload: RecipeWrite, db: DbSession) -> RecipeOut:
    with _catalog_rules():
        recipe = catalog_admin.create_recipe(
            db,
            name=payload.name,
            description=payload.description,
            unit_of_measure_id=payload.unit_of_measure_id,
            lines=_line_inputs(payload),
        )
    db.commit()
    return _recipe_out(db, recipe)


@router.put(
    "/recipes/{recipe_id}",
    response_model=RecipeOut,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def update_catalog_recipe(recipe_id: int, payload: RecipeWrite, db: DbSession) -> RecipeOut:
    with _catalog_rules():
        recipe = catalog_admin.update_recipe(
            db,
            recipe_id,
            name=payload.name,
            description=payload.description,
            unit_of_measure_id=payload.unit_of_measure_id,
            lines=_line_inputs(payload),
        )
    db.commit()
    return _recipe_out(db, recipe)


@router.delete(
    "/recipes/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def deactivate_catalog_recipe(recipe_id: int, db: DbSession) -> None:
    """Take a recipe out of the catalogue. No usage guard (ADR-005 section 6):
    the works that already added it keep computing from its live rows."""
    with _catalog_rules():
        catalog_admin.deactivate_recipe(db, recipe_id)
    db.commit()
