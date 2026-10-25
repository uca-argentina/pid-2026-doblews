"""What the API says and accepts about purchase orders (HU-20, ADR-011)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import UnitRef

# The scale of the take-off (NUMERIC(14,3)), like HU-18's quantity.
Quantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]

OrderStatus = Literal["draft", "issued", "partially_received", "received", "cancelled"]


class NamedRef(BaseModel):
    id: int
    name: str


class PurchaseOrderSummary(BaseModel):
    """One order of a listing: enough to recognise it and know what it is worth."""

    id: int
    # Correlative per firm; the screen shows it as OC-0001 (ADR-011 section 4).
    number: int
    status: OrderStatus
    project: NamedRef
    supplier: NamedRef
    line_count: int
    # Sum of the lines' frozen price x quantity + shipping (ADR-010 section 4).
    estimated_total: Decimal
    currency: str
    created_at: datetime


class PurchaseOrderLineOut(BaseModel):
    """One line of an order, at the price it froze when it was made."""

    id: int
    resource: NamedRef
    unit: UnitRef
    quantity: Decimal
    unit_price: Decimal
    shipping_cost: Decimal
    estimated_total: Decimal


class OrderEvent(BaseModel):
    """One change of status in an order's history: what, when and who (HU-21).

    Read from the order's own columns (created_*, issued_*, cancelled_*): there
    is no event table. HU-22 adds the receipts to the same timeline.
    """

    kind: Literal["created", "issued", "cancelled"]
    at: datetime
    by: NamedRef


class PurchaseOrderOut(PurchaseOrderSummary):
    """An order with its lines and its history, oldest event first."""

    lines: list[PurchaseOrderLineOut]
    history: list[OrderEvent]


class GenerateItem(BaseModel):
    """A material of the work's take-off to order, and from whom.

    supplier_id null means the default: the cheapest offer for what the work
    still needs. A chosen supplier has to offer the material.
    """

    resource_id: int
    supplier_id: int | None = None


class GenerateOrdersIn(BaseModel):
    items: list[GenerateItem] = Field(min_length=1)


class SkippedMaterialOut(BaseModel):
    """A material asked for that no draft got: already all on order, or nobody sells it."""

    resource_id: int
    name: str
    reason: Literal["already_ordered", "no_supplier"]


class GenerateOrdersOut(BaseModel):
    """The drafts generating touched, and the materials it left out."""

    orders: list[PurchaseOrderSummary]
    skipped: list[SkippedMaterialOut]


class OrderLineCreate(BaseModel):
    resource_id: int
    quantity: Quantity


class OrderLineUpdate(BaseModel):
    quantity: Quantity


class OrderLineSupplierChange(BaseModel):
    supplier_id: int
