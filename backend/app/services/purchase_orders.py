"""The rules for generating and editing purchase order drafts (HU-20, ADR-011).

Plain functions that flush and never commit, raising their own exceptions so the
route maps them to status codes in one place, the way suppliers.py does.

firm_id is always an argument, taken by the route from the resolved membership and
never from the request body. Every lookup goes through a firm-scoped repository, so
an order of another firm is simply not found.

What an order costs is HU-18's arithmetic, not a second copy of it: a line's
estimated total is offer_total() over its frozen price and shipping, the same
formula the comparison ranks suppliers by (ADR-010 section 4).
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firm, PurchaseOrder, PurchaseOrderLine
from app.repositories.project_recipe import ProjectRecipeRepository, TakeoffMaterialEntry
from app.repositories.purchase_order import PurchaseOrderLineRepository, PurchaseOrderRepository
from app.repositories.supplier import OfferEntry, SupplierPriceRepository
from app.services.purchasing import CURRENCY, offer_total, rank

DRAFT = "draft"

NOT_A_DRAFT = "Solo se puede modificar una orden en borrador"
NOT_IN_TAKEOFF = "El material no está en el cómputo de la obra"
NOT_OFFERED = "Ese proveedor no ofrece este material en su lista vigente"
ALREADY_IN_ORDER = "La orden ya tiene este material"

# Why a material asked for was left out of the generated drafts. Codes, not
# sentences: the screen words them.
SKIPPED_ALREADY_ORDERED = "already_ordered"
SKIPPED_NO_SUPPLIER = "no_supplier"


class PurchaseOrderNotFoundError(Exception):
    """The order is not this firm's, was discarded, or does not exist. → 404."""


class PurchaseOrderLineNotFoundError(Exception):
    """No live line of that order has this id. → 404."""


class PurchaseOrderStateError(Exception):
    """The order is not in a status that allows this. → 409."""

    def __init__(self, detail: str = NOT_A_DRAFT) -> None:
        super().__init__(detail)
        self.detail = detail


class PurchaseOrderError(Exception):
    """A rule the order's current lines refuse, like a repeated material. → 409."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidPurchaseLineError(Exception):
    """The payload names a material or a supplier the line cannot have. → 422."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class SkippedMaterial:
    """A material asked for that no draft got, and why."""

    resource_id: int
    name: str
    reason: str


@dataclass(frozen=True)
class GenerateResult:
    """The drafts generating touched, and the materials it left out."""

    order_ids: tuple[int, ...]
    skipped: tuple[SkippedMaterial, ...]


def line_total(line: PurchaseOrderLine) -> Decimal:
    """What a line is expected to cost: frozen price times quantity, plus shipping."""
    return offer_total(line.unit_price, line.shipping_cost, line.quantity)


def order_total(lines: Iterable[PurchaseOrderLine]) -> Decimal:
    return sum((line_total(line) for line in lines), start=Decimal("0.00"))


def ordered_quantities(db: Session, firm_id: int, project_id: int) -> dict[int, Decimal]:
    """How much of each material the work already has on order (drafts included)."""
    return PurchaseOrderLineRepository(db, firm_id=firm_id).ordered_by_resource(project_id)


def get_order(db: Session, firm_id: int, order_id: int) -> PurchaseOrder:
    order = PurchaseOrderRepository(db, firm_id=firm_id).get(order_id)
    if order is None:
        raise PurchaseOrderNotFoundError
    return order


def _draft(db: Session, firm_id: int, order_id: int) -> PurchaseOrder:
    """The order, which has to be a draft to be written (ADR-011 section 7, rule 2)."""
    order = get_order(db, firm_id, order_id)
    if order.status != DRAFT:
        raise PurchaseOrderStateError
    return order


def _takeoff_materials(
    db: Session, firm_id: int, project_id: int
) -> dict[int, TakeoffMaterialEntry]:
    """The materials of the work's take-off: what an order of that work may ask for."""
    return {
        entry.resource_id: entry
        for entry in ProjectRecipeRepository(db, firm_id=firm_id).materials(project_id)
        if entry.type == "material"
    }


def _offer(db: Session, firm_id: int, supplier_id: int, resource_id: int) -> OfferEntry:
    """This supplier's live offer for this material, or the reason there is none.

    The same offers the comparison reads: a live row, of a live supplier, for a
    material the catalogue still has (ADR-010 section 7).
    """
    for offer in SupplierPriceRepository(db, firm_id=firm_id).offers([resource_id]):
        if offer.supplier_id == supplier_id:
            return offer
    raise InvalidPurchaseLineError(NOT_OFFERED)


def _next_number(db: Session, firm_id: int) -> int:
    """The next order number of the firm, under a lock on the firm's row.

    ADR-011 section 4: correlative per firm, so the lock is one level above
    ADR-007's per-work one. UNIQUE (firm_id, number) backs it up.
    """
    db.execute(select(Firm.id).where(Firm.id == firm_id).with_for_update())
    return PurchaseOrderRepository(db, firm_id=firm_id).highest_number() + 1


def _draft_for(
    db: Session, firm_id: int, project_id: int, supplier_id: int, created_by: int
) -> PurchaseOrder:
    """The work's draft to this supplier, created if it has none (ADR-011 section 5)."""
    existing = PurchaseOrderRepository(db, firm_id=firm_id).draft_for(project_id, supplier_id)
    if existing is not None:
        return existing
    order = PurchaseOrder(
        firm_id=firm_id,
        project_id=project_id,
        supplier_id=supplier_id,
        number=_next_number(db, firm_id),
        status=DRAFT,
        created_by=created_by,
    )
    db.add(order)
    db.flush()
    return order


def _put_line(
    db: Session, firm_id: int, order: PurchaseOrder, offer: OfferEntry, quantity: Decimal
) -> PurchaseOrderLine:
    """Add `quantity` of the offer's material to the order.

    If the order already has the material, the quantity is added to that line and
    its price stays the one it froze: an order never repeats a material, and a
    price already frozen is not refreshed behind the architect's back.
    """
    existing = PurchaseOrderLineRepository(db, firm_id=firm_id).for_resource(
        order.id, offer.resource_id
    )
    if existing is not None:
        existing.quantity = existing.quantity + quantity
        db.flush()
        return existing
    line = PurchaseOrderLine(
        purchase_order_id=order.id,
        firm_id=firm_id,
        resource_id=offer.resource_id,
        quantity=quantity,
        unit_price=offer.unit_price,
        shipping_cost=offer.shipping_cost,
        currency=CURRENCY,
    )
    db.add(line)
    db.flush()
    return line


def generate(
    db: Session, firm_id: int, project_id: int, resource_ids: Iterable[int], created_by: int
) -> GenerateResult:
    """Drafts for these materials of the work: one per supplier (ADR-011 section 5).

    Each material goes to the cheapest offer for the quantity the work still
    needs — the take-off's, minus what is already on order — at that quantity.
    A material with nothing left to order, or that no supplier offers, is left
    out and returned with its reason. A material that is not in the work's
    take-off is a mistake in the request, not something to skip: 422.
    """
    requested = list(dict.fromkeys(resource_ids))
    materials = _takeoff_materials(db, firm_id, project_id)
    if any(resource_id not in materials for resource_id in requested):
        raise InvalidPurchaseLineError(NOT_IN_TAKEOFF)

    ordered = ordered_quantities(db, firm_id, project_id)
    offers_by_material: dict[int, list[OfferEntry]] = defaultdict(list)
    for offer in SupplierPriceRepository(db, firm_id=firm_id).offers(requested):
        offers_by_material[offer.resource_id].append(offer)

    touched: dict[int, None] = {}
    skipped: list[SkippedMaterial] = []
    for resource_id in requested:
        material = materials[resource_id]
        pending = material.quantity - ordered.get(resource_id, Decimal("0"))
        if pending <= 0:
            skipped.append(SkippedMaterial(resource_id, material.name, SKIPPED_ALREADY_ORDERED))
            continue
        ranked = rank(offers_by_material[resource_id], pending)
        if not ranked:
            skipped.append(SkippedMaterial(resource_id, material.name, SKIPPED_NO_SUPPLIER))
            continue
        # The first of the cheapest: on a tie, the comparison already orders them
        # by supplier name, so the pick does not change between two clicks.
        best = ranked[0]
        offer = next(
            offer
            for offer in offers_by_material[resource_id]
            if offer.supplier_id == best.supplier_id
        )
        order = _draft_for(db, firm_id, project_id, best.supplier_id, created_by)
        _put_line(db, firm_id, order, offer, pending)
        touched[order.id] = None

    return GenerateResult(order_ids=tuple(touched), skipped=tuple(skipped))


def update_line(
    db: Session, firm_id: int, order_id: int, line_id: int, quantity: Decimal
) -> PurchaseOrderLine:
    """Change how much a draft's line asks for. The price stays frozen."""
    order = _draft(db, firm_id, order_id)
    line = PurchaseOrderLineRepository(db, firm_id=firm_id).get(order.id, line_id)
    if line is None:
        raise PurchaseOrderLineNotFoundError
    line.quantity = quantity
    db.flush()
    return line


def add_line(
    db: Session, firm_id: int, order_id: int, resource_id: int, quantity: Decimal
) -> PurchaseOrderLine:
    """Add a material of the work's take-off to a draft, at its supplier's price today."""
    order = _draft(db, firm_id, order_id)
    if resource_id not in _takeoff_materials(db, firm_id, order.project_id):
        raise InvalidPurchaseLineError(NOT_IN_TAKEOFF)
    if PurchaseOrderLineRepository(db, firm_id=firm_id).for_resource(order.id, resource_id):
        raise PurchaseOrderError(ALREADY_IN_ORDER)
    offer = _offer(db, firm_id, order.supplier_id, resource_id)
    return _put_line(db, firm_id, order, offer, quantity)


def deactivate_line(db: Session, firm_id: int, order_id: int, line_id: int) -> None:
    """Take a line out of a draft. A logical removal: the material can be added again."""
    order = _draft(db, firm_id, order_id)
    line = PurchaseOrderLineRepository(db, firm_id=firm_id).get(order.id, line_id)
    if line is None:
        raise PurchaseOrderLineNotFoundError
    line.is_active = False
    db.flush()


def change_line_supplier(
    db: Session, firm_id: int, order_id: int, line_id: int, supplier_id: int, created_by: int
) -> PurchaseOrder:
    """Move a draft's line to another supplier, and return the draft it landed in.

    The line leaves this draft and goes to the work's draft for the new supplier,
    created if needed, at that supplier's price today (ADR-011 section 5). The new
    supplier has to offer the material. Choosing the same supplier changes nothing.
    """
    order = _draft(db, firm_id, order_id)
    line = PurchaseOrderLineRepository(db, firm_id=firm_id).get(order.id, line_id)
    if line is None:
        raise PurchaseOrderLineNotFoundError
    if supplier_id == order.supplier_id:
        return order

    offer = _offer(db, firm_id, supplier_id, line.resource_id)
    target = _draft_for(db, firm_id, order.project_id, supplier_id, created_by)
    line.is_active = False
    db.flush()
    _put_line(db, firm_id, target, offer, line.quantity)
    return target


def discard(db: Session, firm_id: int, order_id: int) -> None:
    """Discard a draft: it leaves every listing and gives its quantities back.

    Not a cancellation, which is HU-21's and keeps the order visible: a discarded
    draft never existed for anyone. It keeps its number (ADR-011 section 4).
    """
    order = _draft(db, firm_id, order_id)
    order.is_active = False
    db.flush()
