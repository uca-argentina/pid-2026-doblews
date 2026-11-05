"""What buying from the same supplier again is worth, and what it adds up to.

HU-23 earns the points, HU-24 turns a total into a level (ADR-012 sections 3
and 5).

Two halves, like services/purchasing.py. The rule is pure: it takes the lines of
an order and what was bought from that supplier before, and answers with a code
and a number per line, so every case of ADR-012 section 3 is tested without a
database. Below it, the one function that writes the entries, called when an
order becomes received.

The numbers live here and nowhere else. Changing one changes what is earned from
then on and never what was earned before: an entry keeps the rule and the points
it was written with (ADR-012 section 4), which is what lets the history explain
each number with the rule that produced it.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import FirmPointsEntry, PurchaseOrder
from app.repositories.loyalty import FirmPointsEntryRepository
from app.repositories.purchase_order import (
    PurchaseOrderLineRepository,
    PurchaseOrderReceiptRepository,
    PurchaseOrderRepository,
)

# The four cases, in the order they are tried.
SAME_MATERIAL_SIMILAR_QUANTITY = "same_material_similar_quantity"
SAME_MATERIAL = "same_material"
SAME_SUPPLIER = "same_supplier"
FIRST_PURCHASE = "first_purchase"

# What each one is worth (ADR-012 section 3). The team's numbers, with no
# empirical backing, which is the reason they are in one place.
POINTS: Mapping[str, int] = {
    SAME_MATERIAL_SIMILAR_QUANTITY: 10,
    SAME_MATERIAL: 6,
    SAME_SUPPLIER: 3,
    FIRST_PURCHASE: 0,
}

# "Similar" is within half of what came last time, the border counting as inside.
SIMILAR_TOLERANCE = Decimal("0.5")


@dataclass(frozen=True)
class PurchasedLine:
    """One line of the order being rated: its material and what arrived of it."""

    line_id: int
    resource_id: int
    quantity: Decimal


@dataclass(frozen=True)
class EarnedPoints:
    """What one line earned, and everything needed to explain it afterwards."""

    line_id: int
    resource_id: int
    rule: str
    points: int
    quantity: Decimal
    # What the quantity was compared against, or None when there was nothing to
    # compare: a material never bought from this supplier, or a first purchase.
    previous_quantity: Decimal | None


def is_similar(quantity: Decimal, previous: Decimal) -> bool:
    """Whether this much counts as "like last time" (ADR-012 section 3).

    |q - previous| <= 0.5 x previous, so exactly half as much or half again both
    count: the border is inside, which is the kinder reading and the one a person
    assumes when told "about the same".
    """
    return abs(quantity - previous) <= SIMILAR_TOLERANCE * previous


def rate(
    lines: Iterable[PurchasedLine],
    previous_quantities: Mapping[int, Decimal],
    *,
    bought_before: bool,
) -> tuple[EarnedPoints, ...]:
    """What each line of a received order earns, by the first rule it meets.

    `previous_quantities` maps a material to what was received of it the last
    time it was bought from this supplier — the most recent received order that
    had it, not necessarily the most recent order at all, so a material bought
    two orders ago still counts as bought.

    `bought_before` says whether the firm had ever received an order from this
    supplier. It cannot be read off `previous_quantities`, because an empty map
    also describes a firm that buys from them often and never bought any of
    these materials: the first earns nothing, the second earns same_supplier.

    The lines of one order are never compared with each other. On a first
    purchase every line is first_purchase, however many there are.
    """
    earned: list[EarnedPoints] = []
    for line in lines:
        previous = previous_quantities.get(line.resource_id)
        if not bought_before:
            rule, compared = FIRST_PURCHASE, None
        elif previous is None:
            rule, compared = SAME_SUPPLIER, None
        elif is_similar(line.quantity, previous):
            rule, compared = SAME_MATERIAL_SIMILAR_QUANTITY, previous
        else:
            rule, compared = SAME_MATERIAL, previous
        earned.append(
            EarnedPoints(
                line_id=line.line_id,
                resource_id=line.resource_id,
                rule=rule,
                points=POINTS[rule],
                quantity=line.quantity,
                previous_quantity=compared,
            )
        )
    return tuple(earned)


def award(db: Session, firm_id: int, order: PurchaseOrder) -> tuple[FirmPointsEntry, ...]:
    """Write the entries of an order that has just become received (ADR-012 section 2).

    Called from the one place that moves an order to received, so the points are
    written in the same transaction as the receipt that completed it: either both
    happen or neither does.

    What is rated is what arrived, not what was ordered — for a received order
    the two agree, but the received quantity is the one the rule is defined over.
    An order whose lines were already rated is left alone, so calling this twice
    writes nothing the second time; the unique index says the same thing one
    level down.
    """
    entries = FirmPointsEntryRepository(db, firm_id=firm_id)
    if entries.rated(order.id):
        return ()

    received = PurchaseOrderReceiptRepository(db, firm_id=firm_id).received_by_line(order.id)
    lines = PurchaseOrderLineRepository(db, firm_id=firm_id)
    purchased = [
        PurchasedLine(
            line_id=entry.line.id,
            resource_id=entry.line.resource_id,
            quantity=received[entry.line.id].quantity,
        )
        for entry in lines.lines([order.id]).get(order.id, [])
        if entry.line.id in received
    ]

    bought_before = PurchaseOrderRepository(db, firm_id=firm_id).received_from(
        order.supplier_id, besides=order.id
    )
    previous_quantities = lines.last_received_quantities(order.supplier_id, besides=order.id)

    written = tuple(
        FirmPointsEntry(
            firm_id=firm_id,
            supplier_id=order.supplier_id,
            purchase_order_id=order.id,
            purchase_order_line_id=points.line_id,
            resource_id=points.resource_id,
            rule=points.rule,
            points=points.points,
            quantity=points.quantity,
            previous_quantity=points.previous_quantity,
        )
        for points in rate(purchased, previous_quantities, bought_before=bought_before)
    )
    db.add_all(written)
    db.flush()
    return written


# --- levels (HU-24, ADR-012 section 5) ----------------------------------------

BRONZE = "bronze"
SILVER = "silver"
GOLD = "gold"
PLATINUM = "platinum"

# Where each level starts, lowest first. Four fixed levels, the same for the firm
# and for each supplier, and not editable from any screen: ADR-012 discarded an
# administration page for something nobody asked to change. They live here beside
# the rule for the same reason its values do — one place to adjust.
LEVELS: tuple[tuple[str, int], ...] = (
    (BRONZE, 0),
    (SILVER, 50),
    (GOLD, 150),
    (PLATINUM, 400),
)


@dataclass(frozen=True)
class LevelStanding:
    """Where a total stands: the level it reached, and what the next one needs.

    The three `next_*` fields are None together, at the top level, where there is
    nothing left to reach. The screen says so instead of drawing a bar that can
    never fill.
    """

    points: int
    level: str
    level_from: int
    next_level: str | None
    next_level_at: int | None
    points_to_next: int | None


def level_for(points: int) -> LevelStanding:
    """The level a total of points reaches, and how far the next one is.

    Pure, like the rule above it: the thresholds are constants, so this is
    tested without a database. A total of zero is Bronce — a firm that has
    received nothing is at the first level, not at none.
    """
    reached = 0
    for index, (_, threshold) in enumerate(LEVELS):
        if points >= threshold:
            reached = index
    level, level_from = LEVELS[reached]

    if reached + 1 == len(LEVELS):
        return LevelStanding(
            points=points,
            level=level,
            level_from=level_from,
            next_level=None,
            next_level_at=None,
            points_to_next=None,
        )
    next_level, next_level_at = LEVELS[reached + 1]
    return LevelStanding(
        points=points,
        level=level,
        level_from=level_from,
        next_level=next_level,
        next_level_at=next_level_at,
        points_to_next=next_level_at - points,
    )
