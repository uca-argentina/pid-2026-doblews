"""The rules of a purchase order's life: drafts, issuing and receipts (ADR-011).

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
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import LOCAL_ZONE, today
from app.models import (
    Firm,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderReceipt,
    PurchaseOrderReceiptLine,
)
from app.repositories.project_recipe import ProjectRecipeRepository, TakeoffMaterialEntry
from app.repositories.purchase_order import (
    PurchaseOrderLineRepository,
    PurchaseOrderReceiptRepository,
    PurchaseOrderRepository,
)
from app.repositories.supplier import OfferEntry, SupplierPriceRepository
from app.services.purchasing import CURRENCY, offer_total, rank

DRAFT = "draft"
ISSUED = "issued"
PARTIALLY_RECEIVED = "partially_received"
RECEIVED = "received"
CANCELLED = "cancelled"
# The two statuses a delivery may be registered against (ADR-011 section 3).
RECEIVABLE = (ISSUED, PARTIALLY_RECEIVED)

NOT_A_DRAFT = "Solo se puede modificar una orden en borrador"
NOT_IN_TAKEOFF = "El material no está en el cómputo de la obra"
NOT_OFFERED = "Ese proveedor no ofrece este material en su lista vigente"
ALREADY_IN_ORDER = "La orden ya tiene este material"
ISSUE_ONLY_DRAFT = "Solo se puede emitir una orden en borrador"
EMPTY_ORDER = "No se puede emitir una orden sin materiales"
CANCELLED_IS_FINAL = "Una orden anulada no cambia de estado"
RECEIVED_NOT_CANCELLABLE = "Una orden con materiales recibidos no se puede anular"
RECEIVE_ONLY_ISSUED = "Solo se puede recibir una orden emitida o recibida parcialmente"
EMPTY_RECEIPT = "Una recepción tiene que registrar al menos un material"
OVER_ORDERED = "No se puede recibir más de lo pedido"
FUTURE_RECEIPT = "Una recepción no puede ser posterior a hoy"
RECEIPT_BEFORE_ISSUE = "Una recepción no puede ser anterior a la emisión de la orden"
NOT_LAST_RECEIPT = "Solo se puede anular la última recepción de la orden"
NO_RECEIPTS = "La orden no tiene recepciones para anular"
REPEATED_RECEIPT_LINE = "Una recepción registra cada material una sola vez"
RECEIVED_IS_CLOSED = "Una orden recibida queda cerrada: no se anulan sus recepciones"

# Why a material asked for was left out of the generated drafts. Codes, not
# sentences: the screen words them.
SKIPPED_ALREADY_ORDERED = "already_ordered"
SKIPPED_NO_SUPPLIER = "no_supplier"

# received_estimate() compares materials only, so it asks offer_total() for a
# total with no freight in it. The freight of a delivery is the receipt's.
_NO_SHIPPING = Decimal("0.00")


class PurchaseOrderNotFoundError(Exception):
    """The order is not this firm's, was discarded, or does not exist. → 404."""


class PurchaseOrderLineNotFoundError(Exception):
    """No live line of that order has this id. → 404."""


class PurchaseOrderReceiptNotFoundError(Exception):
    """No live receipt of that order has this id. → 404."""


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


def received_estimate(line: PurchaseOrderLine, quantity: Decimal) -> Decimal:
    """What the frozen price says this much of the line should have cost (HU-22).

    The material alone. The shipping the line froze is left out on purpose: the
    freight of a delivery belongs to the receipt, which carries it once for the
    whole truck, so charging a share of it to each material would invent a split
    the supplier never made (ADR-011 section 8).

    Expressed through offer_total() with no shipping rather than multiplying
    here, so there is one rounding rule in the project and not two.
    """
    return offer_total(line.unit_price, _NO_SHIPPING, quantity)


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
    db: Session,
    firm_id: int,
    project_id: int,
    items: Iterable[tuple[int, int | None]],
    created_by: int,
) -> GenerateResult:
    """Drafts for these materials of the work: one per supplier (ADR-011 section 5).

    `items` pairs each material with the supplier chosen for it, or None for the
    default: the cheapest offer for the quantity the work still needs. Either
    way the quantity is that one — the take-off's, minus what is already on
    order. A material with nothing left to order, or that no supplier offers
    when none was chosen, is left out and returned with its reason.

    A material that is not in the work's take-off, or a chosen supplier that
    does not offer it, is a mistake in the request and not something to skip:
    422, checked for every item before anything is written.
    """
    requested: dict[int, int | None] = {}
    for resource_id, supplier_id in items:
        requested[resource_id] = supplier_id

    materials = _takeoff_materials(db, firm_id, project_id)
    if any(resource_id not in materials for resource_id in requested):
        raise InvalidPurchaseLineError(NOT_IN_TAKEOFF)

    offers_by_material: dict[int, list[OfferEntry]] = defaultdict(list)
    for offer in SupplierPriceRepository(db, firm_id=firm_id).offers(list(requested)):
        offers_by_material[offer.resource_id].append(offer)

    def offer_of(resource_id: int, supplier_id: int) -> OfferEntry | None:
        return next(
            (o for o in offers_by_material[resource_id] if o.supplier_id == supplier_id),
            None,
        )

    for resource_id, chosen in requested.items():
        if chosen is not None and offer_of(resource_id, chosen) is None:
            raise InvalidPurchaseLineError(NOT_OFFERED)

    ordered = ordered_quantities(db, firm_id, project_id)
    touched: dict[int, None] = {}
    skipped: list[SkippedMaterial] = []
    for resource_id, chosen in requested.items():
        material = materials[resource_id]
        pending = material.quantity - ordered.get(resource_id, Decimal("0"))
        if pending <= 0:
            skipped.append(SkippedMaterial(resource_id, material.name, SKIPPED_ALREADY_ORDERED))
            continue
        if chosen is None:
            ranked = rank(offers_by_material[resource_id], pending)
            if not ranked:
                skipped.append(SkippedMaterial(resource_id, material.name, SKIPPED_NO_SUPPLIER))
                continue
            # The first of the cheapest: on a tie, the comparison already orders
            # them by supplier name, so the pick does not change between clicks.
            chosen = ranked[0].supplier_id
        offer = offer_of(resource_id, chosen)
        order = _draft_for(db, firm_id, project_id, chosen, created_by)
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


def issue(db: Session, firm_id: int, order_id: int, issued_by: int) -> PurchaseOrder:
    """Issue a draft (HU-21): from here on the order is not edited (ADR-011 section 3).

    Only a draft with at least one live line. Anything else is a 409 that says
    why: already issued, cancelled, or empty.
    """
    order = get_order(db, firm_id, order_id)
    if order.status == CANCELLED:
        raise PurchaseOrderStateError(CANCELLED_IS_FINAL)
    if order.status != DRAFT:
        raise PurchaseOrderStateError(ISSUE_ONLY_DRAFT)
    if not PurchaseOrderLineRepository(db, firm_id=firm_id).lines([order.id]):
        raise PurchaseOrderStateError(EMPTY_ORDER)
    order.status = ISSUED
    order.issued_at = func.now()
    order.issued_by = issued_by
    db.flush()
    db.refresh(order)
    return order


def cancel(db: Session, firm_id: int, order_id: int, cancelled_by: int) -> PurchaseOrder:
    """Cancel a draft or an issued order. Final: a cancelled order never moves again.

    An order that already received something cannot be cancelled (ADR-011
    section 3, rule 4). The status check below is that rule: a delivery always
    leaves the order partially_received or received, so an order still issued is
    one nothing arrived for. The order stays visible with its status, unlike a
    discarded draft, and its quantities stop counting as ordered.
    """
    order = get_order(db, firm_id, order_id)
    if order.status == CANCELLED:
        raise PurchaseOrderStateError(CANCELLED_IS_FINAL)
    if order.status not in (DRAFT, ISSUED):
        raise PurchaseOrderStateError(RECEIVED_NOT_CANCELLABLE)
    order.status = CANCELLED
    order.cancelled_at = func.now()
    order.cancelled_by = cancelled_by
    db.flush()
    db.refresh(order)
    return order


# --- receipts (HU-22) ---------------------------------------------------------


@dataclass(frozen=True)
class ReceiptLineIn:
    """One material of a delivery as the request gives it: how much, and what it cost."""

    line_id: int
    quantity: Decimal
    actual_cost: Decimal


def _lock_order(db: Session, firm_id: int, order_id: int) -> None:
    """Hold the order's row for the rest of the transaction.

    Two deliveries registered at the same moment would otherwise both read the
    same "received so far", both pass the ceiling of rule 1, and together leave
    the order with more received than it ever ordered. The lock is on the order
    and not on the receipts because what has to be serialised is the decision
    the whole order's rows are read for.
    """
    db.execute(
        select(PurchaseOrder.id)
        .where(PurchaseOrder.id == order_id, PurchaseOrder.firm_id == firm_id)
        .with_for_update()
    )


def _check_receipt_date(received_on: date, order: PurchaseOrder) -> None:
    """When a delivery may say it arrived.

    Not in the future, measured in Argentina and not on the server
    (core/clock.py), like a task's actual dates. And not before the day the
    order was placed: a delivery of an order that did not exist yet is a typo.

    The issue date is read as the day it was in Argentina for the same reason:
    an order issued at ten at night is already tomorrow in UTC, and a delivery
    that arrived that same day must not be refused for preceding it.
    """
    if received_on > today():
        raise PurchaseOrderError(FUTURE_RECEIPT)
    # Not None for a receivable order: the schema's issued_has_date says so.
    if received_on < order.issued_at.astimezone(LOCAL_ZONE).date():
        raise PurchaseOrderError(RECEIPT_BEFORE_ISSUE)


def _apply_received_status(db: Session, firm_id: int, order: PurchaseOrder) -> PurchaseOrder:
    """Set the order's status from what its live receipts say (ADR-011 section 3).

    The two received statuses are never chosen by anyone: they are derived here,
    after every write that can change what arrived, which is what keeps rule 8
    true. Registering a delivery and cancelling one both end in this function, so
    an order that loses its last receipt walks back to issued by the same path it
    walked forward.

    It is also the one place the step to received happens, and so the place
    HU-23 hangs the points of ADR-012 section 3 off.
    """
    lines = PurchaseOrderLineRepository(db, firm_id=firm_id).lines([order.id]).get(order.id, [])
    received = PurchaseOrderReceiptRepository(db, firm_id=firm_id).received_by_line(order.id)

    def delivered(line: PurchaseOrderLine) -> Decimal:
        totals = received.get(line.id)
        return totals.quantity if totals is not None else Decimal("0")

    anything = any(delivered(entry.line) > 0 for entry in lines)
    everything = bool(lines) and all(
        delivered(entry.line) >= entry.line.quantity for entry in lines
    )

    if everything:
        order.status = RECEIVED
        order.received_at = func.now()
    else:
        order.status = PARTIALLY_RECEIVED if anything else ISSUED
        order.received_at = None
    db.flush()
    db.refresh(order)
    return order


def register_receipt(
    db: Session,
    firm_id: int,
    order_id: int,
    *,
    received_on: date,
    note: str | None,
    shipping_cost: Decimal | None,
    lines: Iterable[ReceiptLineIn],
    created_by: int,
) -> PurchaseOrder:
    """Register what arrived of an order on one day, and what was paid for it (HU-22).

    Only against an order that was issued and is not complete. Nothing may exceed
    what was ordered, counting what earlier live receipts already brought (rule
    1), and a material appears once per delivery.

    The order's status is not given: it is derived from the receipts once this one
    is written, so the caller cannot leave an order saying something its
    deliveries do not.
    """
    _lock_order(db, firm_id, order_id)
    order = get_order(db, firm_id, order_id)
    if order.status not in RECEIVABLE:
        raise PurchaseOrderStateError(RECEIVE_ONLY_ISSUED)
    _check_receipt_date(received_on, order)

    requested = list(lines)
    if not requested:
        raise PurchaseOrderError(EMPTY_RECEIPT)

    ordered = {
        entry.line.id: entry.line
        for entry in PurchaseOrderLineRepository(db, firm_id=firm_id)
        .lines([order.id])
        .get(order.id, [])
    }
    seen: set[int] = set()
    for item in requested:
        if item.line_id in seen:
            raise PurchaseOrderError(REPEATED_RECEIPT_LINE)
        seen.add(item.line_id)
        if item.line_id not in ordered:
            raise PurchaseOrderLineNotFoundError

    already = PurchaseOrderReceiptRepository(db, firm_id=firm_id).received_by_line(order.id)
    for item in requested:
        totals = already.get(item.line_id)
        delivered = totals.quantity if totals is not None else Decimal("0")
        if delivered + item.quantity > ordered[item.line_id].quantity:
            raise PurchaseOrderError(OVER_ORDERED)

    receipt = PurchaseOrderReceipt(
        purchase_order_id=order.id,
        firm_id=firm_id,
        received_on=received_on,
        note=note,
        shipping_cost=shipping_cost,
        created_by=created_by,
    )
    db.add(receipt)
    db.flush()
    for item in requested:
        db.add(
            PurchaseOrderReceiptLine(
                receipt_id=receipt.id,
                purchase_order_line_id=item.line_id,
                quantity=item.quantity,
                actual_cost=item.actual_cost,
            )
        )
    db.flush()
    return _apply_received_status(db, firm_id, order)


def cancel_last_receipt(db: Session, firm_id: int, order_id: int, receipt_id: int) -> PurchaseOrder:
    """Cancel the order's last receipt: the only correction a receipt allows (D-20).

    A receipt is never edited. What is wrong is undone and loaded again, and only
    the last one, so that no later delivery is left standing on a total that no
    longer exists (ADR-011 section 3).

    A received order is closed: it already earned its points (ADR-012 section 2),
    and giving them back is not something this does.
    """
    _lock_order(db, firm_id, order_id)
    order = get_order(db, firm_id, order_id)
    if order.status == RECEIVED:
        raise PurchaseOrderStateError(RECEIVED_IS_CLOSED)
    if order.status != PARTIALLY_RECEIVED:
        raise PurchaseOrderStateError(NO_RECEIPTS)

    receipts = PurchaseOrderReceiptRepository(db, firm_id=firm_id)
    receipt = receipts.get(order.id, receipt_id)
    if receipt is None:
        raise PurchaseOrderReceiptNotFoundError
    last = receipts.last(order.id)
    if last is None or last.id != receipt.id:
        raise PurchaseOrderStateError(NOT_LAST_RECEIPT)

    receipt.is_active = False
    db.flush()
    return _apply_received_status(db, firm_id, order)
