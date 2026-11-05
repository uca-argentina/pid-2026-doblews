"""What the API says and accepts about purchase orders (ADR-011)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.catalog import UnitRef

# The scale of the take-off (NUMERIC(14,3)), like HU-18's quantity.
Quantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
# An amount off an invoice: zero is a real answer (a delivery charged to the
# next one), a negative one is not.
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]

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
    """One line of an order, at the price it froze, and what has arrived of it."""

    id: int
    resource: NamedRef
    unit: UnitRef
    quantity: Decimal
    unit_price: Decimal
    shipping_cost: Decimal
    estimated_total: Decimal

    # What arrived across the order's live receipts, and what is still owed
    # (HU-22). Zero and the whole quantity while nothing has been delivered.
    received_quantity: Decimal
    pending_quantity: Decimal

    # The two halves of the comparison: what the frozen price says the delivered
    # quantity should have cost, and what the invoices actually charged for it.
    # Materials only on both sides — the freight is the receipt's (ADR-011 8).
    received_estimate: Decimal
    actual_cost: Decimal
    # actual_cost - received_estimate: positive is more than agreed. None while
    # nothing has arrived, when there is nothing to compare.
    cost_difference: Decimal | None


class OrderEvent(BaseModel):
    """One change of status in an order's history: what, when and who (HU-21).

    Read from the order's own columns (created_*, issued_*, cancelled_*) and,
    for a delivery, from the receipt itself: there is no event table.
    """

    kind: Literal["created", "issued", "cancelled", "received"]
    at: datetime
    by: NamedRef


class ReceiptLineOut(BaseModel):
    """What arrived of one line in one delivery, and what the invoice charged."""

    purchase_order_line_id: int
    resource: NamedRef
    unit: UnitRef
    quantity: Decimal
    actual_cost: Decimal


class ReceiptOut(BaseModel):
    """One delivery of an order (HU-22), oldest first in the order's detail."""

    id: int
    received_on: date
    note: str | None
    # The freight of this delivery, charged once for the whole truck. None is
    # "the supplier charged none", which is not a zero it charged and wrote down.
    shipping_cost: Decimal | None
    created_by: NamedRef
    created_at: datetime
    lines: list[ReceiptLineOut]
    # What this delivery cost in all: its materials plus its freight.
    total: Decimal
    # Whether this is the receipt the order would cancel, which is the last one
    # loaded on an order that is not yet complete (ADR-011 section 3). Decided
    # here and not in the screen, so the rule lives in one place.
    can_cancel: bool


class PurchaseOrderOut(PurchaseOrderSummary):
    """An order with its lines, its deliveries and its history, oldest event first."""

    lines: list[PurchaseOrderLineOut]
    receipts: list[ReceiptOut]
    history: list[OrderEvent]

    # What the order has really cost so far: every live receipt's materials and
    # freight. Compared against estimated_total only once the order is complete,
    # which the screen is what decides.
    actual_total: Decimal


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


class ReceiptLineIn(BaseModel):
    """One material of a delivery: how much of that line arrived, and what it cost.

    actual_cost is the invoice's amount for this material in this delivery, with
    no freight in it: the delivery's freight is the receipt's own field.
    """

    line_id: int
    quantity: Quantity
    actual_cost: Money


class ReceiptIn(BaseModel):
    """A delivery of an order: a day, what arrived, and what was paid for it."""

    received_on: date
    note: str | None = Field(default=None, max_length=150)
    shipping_cost: Money | None = None
    lines: list[ReceiptLineIn] = Field(min_length=1)
