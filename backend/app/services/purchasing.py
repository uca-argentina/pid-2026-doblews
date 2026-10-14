"""Comparing what each supplier asks for a material (HU-18, ADR-010 section 4).

Two halves. The arithmetic is pure, like services/projection.py: no session and
no SQL, so the formula, the order and the ties are tested without a database.
The two builders below it read what that arithmetic needs, for one material or
for every material of a work.

Nothing is stored. The cheapest offer depends on the quantity and on prices
that change, so it is computed on every read, and no choice of supplier is ever
recorded: the request is to show the cheapest one, not to buy from it.

The comparison is material by material. There is no total for buying a whole
work: adding up each material's cheapest offer would read as an optimal
purchase, which the request explicitly leaves out.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.models import UnitOfMeasure
from app.repositories.project_recipe import ProjectRecipeRepository
from app.repositories.supplier import OfferEntry, SupplierPriceRepository, SupplierRepository
from app.services.catalog import UnitLabel
from app.services.suppliers import priceable_material

# The take-off fixes the currency to ARS (HU-5), and a supplier's row defaults to
# it. The column exists on both for the day a second one arrives.
CURRENCY = "ARS"

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class RankedOffer:
    """One supplier's offer for a quantity: what it costs in all, and whether it wins."""

    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    shipping_cost: Decimal
    price_updated_at: datetime
    total: Decimal
    cheapest: bool


@dataclass(frozen=True)
class MaterialComparison:
    """Every offer for one material, at one quantity, cheapest first."""

    resource_id: int
    name: str
    unit: UnitLabel
    quantity: Decimal
    reference_price: Decimal
    # The same quantity at the catalogue's reference price: what the budget
    # counts it at, shown beside the offers and always labelled as such.
    reference_total: Decimal
    offers: tuple[RankedOffer, ...]


def offer_total(unit_price: Decimal, shipping_cost: Decimal, quantity: Decimal) -> Decimal:
    """What buying `quantity` from this supplier costs: price times quantity, plus shipping.

    ADR-010 section 4. The product is rounded to the cent before the shipping is
    added, half away from zero like Postgres' round(), which is how the take-off
    rounds its costs: the totals of both screens are rounded the same way.
    """
    return (unit_price * quantity).quantize(_CENT, rounding=ROUND_HALF_UP) + shipping_cost


def rank(offers: Iterable[OfferEntry], quantity: Decimal) -> tuple[RankedOffer, ...]:
    """The offers for one material, cheapest first, with every cheapest one marked.

    A tie marks them all (HU-18): neither is more economical than the other, so
    picking one would be arbitrary. Equal totals are ordered by supplier name, so
    the list does not reshuffle between two reads.
    """
    totals = [
        (offer, offer_total(offer.unit_price, offer.shipping_cost, quantity)) for offer in offers
    ]
    if not totals:
        return ()
    lowest = min(total for _, total in totals)
    totals.sort(key=lambda pair: (pair[1], pair[0].supplier_name.lower(), pair[0].supplier_id))
    return tuple(
        RankedOffer(
            supplier_id=offer.supplier_id,
            supplier_name=offer.supplier_name,
            unit_price=offer.unit_price,
            shipping_cost=offer.shipping_cost,
            price_updated_at=offer.price_updated_at,
            total=total,
            cheapest=total == lowest,
        )
        for offer, total in totals
    )


def compare_material(
    db: Session, *, firm_id: int, resource_id: int, quantity: Decimal
) -> MaterialComparison:
    """Every offer this firm's suppliers make for one material, for a quantity.

    The material must be one a list may carry (ADR-010 section 7, rules 1 and 2):
    an active material of the catalogue. Anything else raises the same
    InvalidMaterialError HU-17 raises when pricing it, and the route answers 422.
    """
    resource = priceable_material(db, resource_id)
    unit = db.get(UnitOfMeasure, resource.unit_of_measure_id)
    offers = SupplierPriceRepository(db, firm_id=firm_id).offers([resource.id])
    return MaterialComparison(
        resource_id=resource.id,
        name=resource.name,
        unit=UnitLabel(unit.code, unit.abbreviation),
        quantity=quantity,
        reference_price=resource.reference_price,
        reference_total=offer_total(resource.reference_price, Decimal("0"), quantity),
        offers=rank(offers, quantity),
    )


def project_purchasing(
    db: Session, *, firm_id: int, project_id: int
) -> tuple[MaterialComparison, ...]:
    """Each material of a work's take-off, compared at the quantity the work needs.

    Only materials: labour and equipment are not bought from a supplier's list.
    Every material of the take-off comes back, offered or not: one that no
    supplier lists, or that the catalogue has since retired, has no offers and
    is shown as "sin proveedor" with its reference price.

    The quantity and the reference cost are HU-5's own, already rounded per
    material, so this screen and the budget agree on both. The offers come from
    the work's own firm only (ADR-010 section 7, rule 5): firm_id is the one the
    route resolved the work under.
    """
    materials = [
        entry
        for entry in ProjectRecipeRepository(db, firm_id=firm_id).materials(project_id)
        if entry.type == "material"
    ]
    offers_by_material: dict[int, list[OfferEntry]] = defaultdict(list)
    for offer in SupplierPriceRepository(db, firm_id=firm_id).offers(
        [entry.resource_id for entry in materials]
    ):
        offers_by_material[offer.resource_id].append(offer)

    return tuple(
        MaterialComparison(
            resource_id=entry.resource_id,
            name=entry.name,
            unit=entry.unit,
            quantity=entry.quantity,
            reference_price=entry.unit_price,
            reference_total=entry.cost,
            offers=rank(offers_by_material[entry.resource_id], entry.quantity),
        )
        for entry in materials
    )


def firm_has_suppliers(db: Session, *, firm_id: int) -> bool:
    """Whether there is anything to compare at all: the screens' empty state."""
    return SupplierRepository(db, firm_id=firm_id).any()
