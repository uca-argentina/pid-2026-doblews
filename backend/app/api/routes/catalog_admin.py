"""Support's catalogue admin screens: resources and recipes (HU-8, ADR-005).

Under /platform/catalog and never under /firms/{firm_id}: the catalogue belongs
to no firm, and support belongs to no roster (same reasoning as platform.py for
HU-7). Every route here demands catalog.manage in platform scope, which is what
keeps this out of every firm's reach — an owner or an architect gets 403.

The read side reuses app.services.catalog as is: GET here returns exactly what
HU-4's screens show everyone else, because it is the same catalogue. Only the
write responses are shaped from the row catalog_admin.py just wrote, with the
helpers app.api.catalog_common shares with a firm's own recipe routes (HU-9).
"""

from fastapi import APIRouter, Depends, status

from app.api.catalog_common import catalog_rules, line_inputs, recipe_out, unit_ref
from app.api.deps import DbSession, requires
from app.models import Resource
from app.schemas.catalog import RecipeOut, ResourceOut
from app.schemas.catalog_admin import RecipeWrite, ResourceWrite
from app.services import catalog, catalog_admin

router = APIRouter(prefix="/platform/catalog", tags=["catalog-admin"])


def _resource_out(db: DbSession, resource: Resource) -> ResourceOut:
    """The row a write just produced, in the same shape HU-4's listing uses."""
    return ResourceOut(
        id=resource.id,
        type=resource.type,
        name=resource.name,
        unit=unit_ref(db, resource.unit_of_measure_id),
        reference_price=resource.reference_price,
        currency=resource.currency,
        price_updated_at=resource.price_updated_at,
    )


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
    with catalog_rules():
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
    with catalog_rules():
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
    with catalog_rules():
        catalog_admin.deactivate_resource(db, resource_id)
    db.commit()


@router.get(
    "/recipes",
    response_model=list[RecipeOut],
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def list_catalog_recipes(db: DbSession) -> list[RecipeOut]:
    """Every active general recipe with its lines. Never a firm's own (ADR-006)."""
    return [
        RecipeOut.model_validate(entry, from_attributes=True)
        for entry in catalog.list_recipes(db, firm_id=None)
    ]


@router.post(
    "/recipes",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def create_catalog_recipe(payload: RecipeWrite, db: DbSession) -> RecipeOut:
    with catalog_rules():
        recipe = catalog_admin.create_recipe(
            db,
            name=payload.name,
            description=payload.description,
            unit_of_measure_id=payload.unit_of_measure_id,
            lines=line_inputs(payload),
        )
    db.commit()
    return recipe_out(db, recipe)


@router.put(
    "/recipes/{recipe_id}",
    response_model=RecipeOut,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def update_catalog_recipe(recipe_id: int, payload: RecipeWrite, db: DbSession) -> RecipeOut:
    with catalog_rules():
        recipe = catalog_admin.update_recipe(
            db,
            recipe_id,
            name=payload.name,
            description=payload.description,
            unit_of_measure_id=payload.unit_of_measure_id,
            lines=line_inputs(payload),
        )
    db.commit()
    return recipe_out(db, recipe)


@router.delete(
    "/recipes/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("catalog.manage", "platform"))],
)
def deactivate_catalog_recipe(recipe_id: int, db: DbSession) -> None:
    """Take a recipe out of the catalogue. No usage guard (ADR-005 section 6):
    the works that already added it keep computing from its live rows."""
    with catalog_rules():
        catalog_admin.deactivate_recipe(db, recipe_id)
    db.commit()
