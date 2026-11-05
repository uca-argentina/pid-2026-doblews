"""What the API says about points and levels (HU-24, ADR-012 sections 5 and 7)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.catalog import UnitRef
from app.schemas.purchase_order import NamedRef
from app.services.loyalty import level_for

PointsRule = Literal[
    "same_material_similar_quantity",
    "same_material",
    "same_supplier",
    "first_purchase",
]

Level = Literal["bronze", "silver", "gold", "platinum"]


class LevelOut(BaseModel):
    """Where a points total stands, for the firm or with one supplier.

    The three next_* fields are null together, at the top level: there is nothing
    left to reach, and the screen says so rather than drawing a bar that cannot
    fill.
    """

    points: int
    level: Level
    # Where the current level starts, so a bar can be drawn between the two
    # thresholds instead of from zero.
    level_from: int
    next_level: Level | None
    next_level_at: int | None
    points_to_next: int | None


def level_of(points: int) -> LevelOut:
    """A total as the API describes it, for the firm or with one supplier.

    Here and not in either route, so the two screens that show a level cannot
    describe one differently. The service answers with a dataclass of the same
    field names, so there is no mapping to keep in step.
    """
    return LevelOut.model_validate(level_for(points), from_attributes=True)


class OrderRef(BaseModel):
    """The order an entry came from, by the number the screens show it as."""

    id: int
    number: int


class PointsEntryOut(BaseModel):
    """One line of the history: what earned what, and why (ADR-012 section 7)."""

    id: int
    earned_at: datetime
    points: int
    # The code, not a sentence: the screen words it, like the skipped materials
    # of HU-20 and the task standings of HU-16.
    rule: PointsRule
    quantity: Decimal
    # What the quantity was compared against, so the history can say "como la
    # vez pasada (1.000 u)". Null for the two rules that compare nothing.
    previous_quantity: Decimal | None
    order: OrderRef
    project: NamedRef
    supplier: NamedRef
    resource: NamedRef
    unit: UnitRef


class LoyaltyOut(BaseModel):
    """The firm's standing and how it got there, newest first."""

    firm: LevelOut
    history: list[PointsEntryOut]
