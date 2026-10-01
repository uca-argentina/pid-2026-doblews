"""A work's estimated budget over HTTP (HU-11): read-only, and only for whoever may see costs.

One endpoint, one guard. The budget is derived entirely from the take-off, so
there is nothing to write here: HU-5's line endpoints are what changes it.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires_any,
)
from app.repositories.project import ProjectRepository
from app.schemas.budget import BudgetGroupOut, BudgetItemOut, BudgetOut
from app.schemas.catalog import UnitRef
from app.services.budget import build_budget

router = APIRouter(prefix="/firms/{firm_id}/projects/{project_id}/budget", tags=["budget"])


@router.get(
    "",
    response_model=BudgetOut,
    dependencies=[
        Depends(
            requires_any(
                ("project.cost.view", "project"),
                ("project.view_all", "firm"),
            )
        )
    ],
)
def read_budget(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> BudgetOut:
    """The estimated budget of a work, grouped into materials, labour and equipment.

    The guard is where HU-11 differs from HU-5, and it is the whole reason this
    is a separate endpoint. The take-off asks for project.recipe.view and empties
    the costs for whoever lacks project.cost.view, so the client of the work sees
    their quantities. Here project.cost.view is the entry condition: the client
    does not hold it and gets a 403, which is what "el client no ve la sección"
    means at the border.

    project.view_all is the owner's second way in, as everywhere else: they audit
    a work of their firm they are not a member of, so they have no project_member
    row to carry project.cost.view.

    The 404 for a work out of reach is resolved after the guard, as in HU-5: the
    guard proves the caller holds something on this work, get_visible proves the
    work is still active and theirs to see.
    """
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account.id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    budget = build_budget(db, firm_id=membership.firm_id, project_id=project.id)

    return BudgetOut(
        groups=[
            BudgetGroupOut(
                type=group.type,
                items=[
                    BudgetItemOut(
                        resource_id=item.resource_id,
                        name=item.name,
                        unit=UnitRef(code=item.unit.code, abbreviation=item.unit.abbreviation),
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        subtotal=item.subtotal,
                    )
                    for item in group.items
                ],
                subtotal=group.subtotal,
            )
            for group in budget.groups
        ],
        total=budget.total,
        currency=budget.currency,
        prices_as_of=budget.prices_as_of,
    )
