"""The firm the caller is currently acting in."""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership, FirmPermissions, requires
from app.schemas.firm import FirmDetail, RoleOut

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get(
    "/{firm_id}",
    response_model=FirmDetail,
    dependencies=[Depends(requires("firm.view", "firm"))],
)
def read_firm(membership: CurrentMembership, permissions: FirmPermissions) -> FirmDetail:
    """The active firm and what I may do in it, or a 404 if it is not one of mine.

    Everything it returns was already resolved by the dependencies, so this
    costs no extra query. The permission set included: requires("firm.view")
    had to resolve it to guard the route, and FastAPI caches a dependency's
    result for the rest of the request.

    It exists for three reasons: the frontend layout needs the firm's name for
    its header, it needs the permissions to decide which sections to show, and
    it is the endpoint the cross-tenant isolation test that ADR-002 section 8
    requires is written against.

    Declaring firm.view changes no behaviour today, since all three firm roles
    hold it. That is the point: the endpoint stops being authorized by accident
    and starts saying what it demands.
    """
    return FirmDetail(
        id=membership.firm_id,
        name=membership.firm_name,
        role=RoleOut(code=membership.role_code, name=membership.role_name),
        permissions=sorted(permissions),
    )
