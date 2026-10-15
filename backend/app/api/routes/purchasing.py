"""Comparing suppliers over HTTP (HU-18, ADR-010 section 8): two reads, nothing written.

Two doors with two different guards, because they answer to different people.
Comparing one material is part of the suppliers section, so it demands what
reading that section demands: supplier.view. Comparing a work's materials is
part of the work, and shows what it would cost to buy, so it demands what
seeing the work's costs demands — the same rule as its budget. Neither opens to
the client.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires,
    requires_any,
)
from app.repositories.project import ProjectRepository
from app.schemas.catalog import UnitRef
from app.schemas.purchasing import (
    ComparedMaterial,
    MaterialComparisonOut,
    OfferOut,
    ProjectPurchasingOut,
)
from app.services import purchasing, suppliers

router = APIRouter(tags=["purchasing"])

# The scale of the take-off's quantities (NUMERIC with 3 decimals): a comparison
# at a quantity no work could need would be a number nobody can check.
Quantity = Annotated[Decimal, Query(gt=0, max_digits=14, decimal_places=3)]


def _compared(material: purchasing.MaterialComparison) -> ComparedMaterial:
    return ComparedMaterial(
        resource_id=material.resource_id,
        name=material.name,
        unit=UnitRef(code=material.unit.code, abbreviation=material.unit.abbreviation),
        quantity=material.quantity,
        reference_price=material.reference_price,
        reference_total=material.reference_total,
        offers=[
            OfferOut(
                supplier_id=offer.supplier_id,
                supplier_name=offer.supplier_name,
                unit_price=offer.unit_price,
                shipping_cost=offer.shipping_cost,
                total=offer.total,
                cheapest=offer.cheapest,
                price_updated_at=offer.price_updated_at,
            )
            for offer in material.offers
        ],
    )


@router.get(
    "/firms/{firm_id}/purchasing/compare",
    response_model=MaterialComparisonOut,
    dependencies=[Depends(requires("supplier.view", "firm"))],
)
def compare_material(
    resource_id: int,
    db: DbSession,
    membership: CurrentMembership,
    quantity: Quantity = Decimal("1"),
) -> MaterialComparisonOut:
    """Every offer this firm has for one material, cheapest first, for a quantity.

    The quantity is the user's, 1 when not given (HU-18). A material that cannot
    be on a list — labour, equipment, a retired or missing one — is a 422, as when
    HU-17 is asked to price it: the request is well formed, what it names is not.
    """
    try:
        material = purchasing.compare_material(
            db, firm_id=membership.firm_id, resource_id=resource_id, quantity=quantity
        )
    except suppliers.InvalidMaterialError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.detail) from None

    return MaterialComparisonOut(
        **_compared(material).model_dump(),
        currency=purchasing.CURRENCY,
        has_suppliers=purchasing.firm_has_suppliers(db, firm_id=membership.firm_id),
    )


@router.get(
    "/firms/{firm_id}/projects/{project_id}/purchasing",
    response_model=ProjectPurchasingOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.cost.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_project_purchasing(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> ProjectPurchasingOut:
    """Each material of the work's take-off, with the cheapest offer for its quantity.

    No new permission (ADR-010 section 6): the same guard as the budget, since
    this is the work's costs too. The 404 for a work out of reach is resolved
    after the guard, as there.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account.id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    materials = purchasing.project_purchasing(db, firm_id=membership.firm_id, project_id=project.id)
    return ProjectPurchasingOut(
        items=[_compared(material) for material in materials],
        currency=purchasing.CURRENCY,
        has_suppliers=purchasing.firm_has_suppliers(db, firm_id=membership.firm_id),
    )
