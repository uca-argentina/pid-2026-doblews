"""What the API says about a work's estimated budget (HU-11).

No cost field is nullable here, unlike HU-5's take-off: this whole section is
behind project.cost.view, so whoever gets an answer gets the numbers. That is
why it is its own endpoint and not a richer /takeoff — the client reads the
take-off with its costs emptied, and must not read this at all.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.catalog import UnitRef
from app.schemas.catalog_admin import ResourceType


class BudgetItemOut(BaseModel):
    """One resource of the budget, as a row of its group's table."""

    resource_id: int
    name: str
    unit: UnitRef
    quantity: Decimal
    # The reference price of one unit: per brick, and per hour for labour and
    # equipment, where the unit is `h` (T-06).
    unit_price: Decimal
    subtotal: Decimal


class BudgetGroupOut(BaseModel):
    """One of the three groups: materials, labour or equipment.

    The three always travel, empty ones included, so the frontend reads one
    shape and decides what to render instead of inferring it from what arrived.
    """

    type: ResourceType
    items: list[BudgetItemOut]
    subtotal: Decimal


class BudgetOut(BaseModel):
    """A work's estimated budget: the three groups and what they add up to.

    total is the sum of the subtotals as shown, which are themselves sums of the
    rounded subtotals of their items, so the screen adds up exactly (HU-5).
    """

    groups: list[BudgetGroupOut]
    total: Decimal
    currency: str
    # "Precios de referencia al <fecha>" (ADR-005 section 5): the oldest price
    # the budget is built from. null when the work has no lines to price.
    prices_as_of: datetime | None
