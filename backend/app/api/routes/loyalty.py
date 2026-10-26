"""The firm's points and level over HTTP (HU-24, ADR-012 section 7).

One read, and nothing writes here: the entries are written by the orders, when
one becomes received (HU-23).

It demands purchase_order.view and not a permission of its own (D-22): the points
come from the orders, and whoever sees the orders sees what they earned. The
client of a firm holds neither, so this section does not exist for them — a 403
and not an empty page.
"""

from fastapi import APIRouter, Depends

from app.api.deps import CurrentMembership, DbSession, requires
from app.repositories.loyalty import FirmPointsEntryRepository, PointsHistoryEntry
from app.schemas.catalog import UnitRef
from app.schemas.loyalty import LoyaltyOut, OrderRef, PointsEntryOut, level_of
from app.schemas.purchase_order import NamedRef

router = APIRouter(prefix="/firms/{firm_id}/loyalty", tags=["loyalty"])

VIEW = requires("purchase_order.view", "firm")


def _entry_out(entry: PointsHistoryEntry) -> PointsEntryOut:
    return PointsEntryOut(
        id=entry.id,
        earned_at=entry.earned_at,
        points=entry.points,
        rule=entry.rule,
        quantity=entry.quantity,
        previous_quantity=entry.previous_quantity,
        order=OrderRef(id=entry.order_id, number=entry.order_number),
        project=NamedRef(id=entry.project_id, name=entry.project_name),
        supplier=NamedRef(id=entry.supplier_id, name=entry.supplier_name),
        resource=NamedRef(id=entry.resource_id, name=entry.resource_name),
        unit=UnitRef(code=entry.unit_code, abbreviation=entry.unit_abbreviation),
    )


@router.get("", response_model=LoyaltyOut, dependencies=[Depends(VIEW)])
def read_loyalty(db: DbSession, membership: CurrentMembership) -> LoyaltyOut:
    """The firm's level and every entry behind it, newest first.

    A firm that has received nothing answers with Bronce at zero and an empty
    history, which is what the screen's empty state is drawn from.
    """
    entries = FirmPointsEntryRepository(db, firm_id=membership.firm_id)
    return LoyaltyOut(
        firm=level_of(entries.total()),
        history=[_entry_out(entry) for entry in entries.history()],
    )
