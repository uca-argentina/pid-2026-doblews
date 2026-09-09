"""The firm the caller is currently acting in."""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership, requires
from app.schemas.firm import FirmSummary, RoleOut

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get(
    "/{firm_id}",
    response_model=FirmSummary,
    dependencies=[Depends(requires("firm.view", "firm"))],
)
def read_firm(membership: CurrentMembership) -> FirmSummary:
    """The active firm, or a 404 if it is not one of mine.

    Everything it returns was already resolved by the dependencies, so this
    costs no extra query. It exists for two reasons: the frontend layout needs
    the firm's name for its header, and it is the endpoint the cross-tenant
    isolation test that ADR-002 section 8 requires is written against.

    Declaring firm.view changes no behaviour today, since all three firm roles
    hold it. That is the point: the endpoint stops being authorized by accident
    and starts saying what it demands.
    """
    return FirmSummary(
        id=membership.firm_id,
        name=membership.firm_name,
        role=RoleOut(code=membership.role_code, name=membership.role_name),
    )
