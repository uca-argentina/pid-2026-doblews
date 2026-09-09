"""The firm the caller is currently acting in."""

from fastapi import APIRouter

from app.api.deps import CurrentMembership
from app.schemas.firm import FirmSummary, RoleOut

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get("/{firm_id}", response_model=FirmSummary)
def read_firm(membership: CurrentMembership) -> FirmSummary:
    """The active firm, or a 404 if it is not one of mine.

    Everything it returns was already resolved by the dependency, so this costs
    no extra query. It exists for two reasons: the frontend layout needs the
    firm's name for its header, and it is the first endpoint the cross-tenant
    isolation test that ADR-002 section 8 requires can be written against.

    TODO(T-03): add Depends(requires("firm.view")). Today the roster check is
    the only authorization here, which is coarser than the ADR asks for. It
    grants nothing extra in the meantime: all three firm roles hold firm.view,
    so the coarse check and the permission check have the same answer.
    """
    return FirmSummary(
        id=membership.firm_id,
        name=membership.firm_name,
        role=RoleOut(code=membership.role_code, name=membership.role_name),
    )
