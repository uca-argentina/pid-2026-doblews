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


class PurchaseOrderOut(PurchaseOrderSummary):
    """An order with its lines."""

    lines: list[PurchaseOrderLineOut]


class GenerateOrdersIn(BaseModel):
    """The materials of the work's take-off to order."""

    resource_ids: list[int] = Field(min_length=1)


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
