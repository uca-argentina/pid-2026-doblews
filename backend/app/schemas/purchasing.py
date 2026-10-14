"""What the API says about comparing suppliers (HU-18, ADR-010 section 4)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.catalog import UnitRef


class OfferOut(BaseModel):
    """One supplier's offer for a material, at the quantity being compared."""

    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    shipping_cost: Decimal
    # round(unit_price x quantity, 2) + shipping_cost.
    total: Decimal
    # True for every offer tied at the lowest total, not only the first.
    cheapest: bool
    price_updated_at: datetime


class ComparedMaterial(BaseModel):
    """A material, the quantity it is compared at, and every offer for it.

    offers is ordered cheapest first and empty when no live supplier lists the
    material: the screen's "sin proveedor".
    """

    resource_id: int
    name: str
    unit: UnitRef
    quantity: Decimal
    # The catalogue's price, the one the budget computes with (ADR-010 section 5),
    # and the same quantity at it. Labelled as such on screen, beside the offers.
    reference_price: Decimal
    reference_total: Decimal
    offers: list[OfferOut]


class MaterialComparisonOut(ComparedMaterial):
    """The comparison for one material, from the suppliers section."""

    currency: str
    # False when the firm has no live supplier: the empty state, which asks for
    # the first one rather than saying this material has none.
    has_suppliers: bool


class ProjectPurchasingOut(BaseModel):
    """Each material of a work's take-off, compared at the quantity the work needs.

    No grand total: adding the cheapest offer of each material would read as an
    optimal purchase, which HU-18 leaves out.
    """

    items: list[ComparedMaterial]
    currency: str
    has_suppliers: bool
