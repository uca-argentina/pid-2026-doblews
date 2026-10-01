"""The catalogue as a firm member sees it (HU-4), and the firm's own recipes (HU-9).

Reads demand catalog.view, which every firm role holds. Writes reach only this
firm's recipes and demand recipe.manage (ADR-006 section 3): the general ones
stay support's, through HU-8's /platform/catalog.
"""

from fastapi import APIRouter, Depends, status

from app.api.catalog_common import catalog_rules, line_inputs, recipe_out
from app.api.deps import CurrentMembership, DbSession, requires
from app.schemas.catalog import RecipeOut, ResourceOut
from app.schemas.catalog_admin import RecipeWrite
from app.services import firm_recipes
from app.services.catalog import list_recipes, list_resources

# Under the firm although the rows are global. catalog.view is a firm-scope
# permission (ADR-003 section 8), and a firm-scope permission needs a firm in the
# path to be resolved against. That also puts these routes in the isolation
# suite of test_route_permissions.py like any other, instead of on its list of
# exceptions: someone outside the firm gets the same 404 as everywhere else.
router = APIRouter(prefix="/firms/{firm_id}/catalog", tags=["catalog"])


@router.get(
    "/recipes",
    response_model=list[RecipeOut],
    dependencies=[Depends(requires("catalog.view", "firm"))],
)
def read_recipes(db: DbSession, membership: CurrentMembership) -> list[RecipeOut]:
    """Every active recipe this firm can use: the general ones and its own.

    The whole list in one response and no search parameter: the catalogue is
    small enough that the browser filters it, and HU-5's picker reuses the same
    cached answer instead of asking again per keystroke.

    The firm comes from the resolved membership and never from the raw path,
    like every other firm route.
    """
    entries = list_recipes(db, firm_id=membership.firm_id)
    return [RecipeOut.model_validate(entry, from_attributes=True) for entry in entries]


@router.post(
    "/recipes",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("recipe.manage", "firm"))],
)
def create_firm_recipe(
    payload: RecipeWrite, db: DbSession, membership: CurrentMembership
) -> RecipeOut:
    """Add a recipe of this firm. firm_id comes from the membership, never the body."""
    with catalog_rules():
        recipe = firm_recipes.create_firm_recipe(
            db,
            membership.firm_id,
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
    dependencies=[Depends(requires("recipe.manage", "firm"))],
)
def update_firm_recipe(
    recipe_id: int, payload: RecipeWrite, db: DbSession, membership: CurrentMembership
) -> RecipeOut:
    """Replace one of this firm's recipes. A general or another firm's is a 404."""
    with catalog_rules():
        recipe = firm_recipes.update_firm_recipe(
            db,
            membership.firm_id,
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
    dependencies=[Depends(requires("recipe.manage", "firm"))],
)
def deactivate_firm_recipe(recipe_id: int, db: DbSession, membership: CurrentMembership) -> None:
    """Take one of this firm's recipes out of use. The works already using it keep
    computing (ADR-005 section 6). A general or another firm's is a 404."""
    with catalog_rules():
        firm_recipes.deactivate_firm_recipe(db, membership.firm_id, recipe_id)
    db.commit()


@router.get(
    "/resources",
    response_model=list[ResourceOut],
    dependencies=[Depends(requires("catalog.view", "firm"))],
)
def read_resources(db: DbSession) -> list[ResourceOut]:
    """Every active resource with its reference price.

    The client role holds catalog.view too, and sees these prices: they are the
    platform's reference prices, the same for every firm, not what a work costs
    the firm. That cost is HU-5's, behind project.cost.view.
    """
    return [ResourceOut.model_validate(entry, from_attributes=True) for entry in list_resources(db)]
