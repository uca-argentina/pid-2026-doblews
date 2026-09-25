"""The system catalogue as a firm member reads it: recipes and materials (HU-4)."""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership, DbSession, requires
from app.schemas.catalog import RecipeOut, ResourceOut
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
