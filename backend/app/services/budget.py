"""The estimated budget of a work (HU-11): the take-off, grouped and priced.

The numbers are the ones HU-5 already computes — this adds no arithmetic of its
own beyond adding up what the repository rounded. What it does add is the shape:
three groups in a fixed order, each with its own subtotal, and a grand total.

A service and not a few lines in the route because HU-12 freezes exactly this:
the version it saves copies these items with their prices, so both have to be
reading the same thing.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.project_recipe import ProjectRecipeRepository, TakeoffMaterialEntry
from app.services.catalog import UnitLabel

# The three groups the screen shows, in the order it shows them: what the work is
# built of, who builds it, and what they build it with. The order is fixed here
# and not left to the database, so it does not depend on how resources are named.
BUDGET_GROUPS: tuple[str, ...] = ("material", "labor", "equipment")

# HU-5 fixes the currency to ARS; the budget sums the same rows, so it cannot
# differ. The column exists on every resource for the day a second one arrives.
CURRENCY = "ARS"

_ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BudgetItem:
    """One resource of the budget: how much of it, at what price, for how much."""

    resource_id: int
    name: str
    unit: UnitLabel
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class BudgetGroup:
    """One of the three groups, with the items it holds and what they add up to."""

    type: str
    items: tuple[BudgetItem, ...]
    subtotal: Decimal


@dataclass(frozen=True)
class Budget:
    """A work's whole estimated budget, ready to render or to freeze."""

    groups: tuple[BudgetGroup, ...]
    total: Decimal
    currency: str
    prices_as_of: datetime | None


def _item(entry: TakeoffMaterialEntry) -> BudgetItem:
    return BudgetItem(
        resource_id=entry.resource_id,
        name=entry.name,
        unit=entry.unit,
        quantity=entry.quantity,
        unit_price=entry.unit_price,
        # The cost the repository already rounded per resource. Not recomputed
        # from quantity x unit_price here: that would round a second time and the
        # column on screen would stop adding up to the subtotal below it.
        subtotal=entry.cost,
    )


def build_budget(db: Session, *, firm_id: int, project_id: int) -> Budget:
    """The budget of a work, computed from its live take-off lines.

    Nothing is stored: it is the draft, recomputed on every read, so editing a
    line or correcting a price in the catalogue changes it with no further step.
    HU-12 is what turns a moment of this into something that stops moving.

    The three groups are always returned, empty ones included, so the response
    has one shape and the screen decides what to render. A work with no lines
    comes back as three empty groups and a total of 0.00, which is the empty
    state.

    Every sum adds already rounded amounts — the subtotal from the items shown,
    the total from the subtotals shown — so what the screen displays adds up
    exactly, as in HU-5.
    """
    entries = ProjectRecipeRepository(db, firm_id=firm_id).materials(project_id)
    by_type: dict[str, list[BudgetItem]] = {group: [] for group in BUDGET_GROUPS}
    # A type outside the three raises here rather than being dropped: resource's
    # CHECK already refuses one, so it could only arrive through a migration that
    # widened it, and a group silently missing from the total is worse than a 500
    # naming the day it was widened.
    for entry in entries:
        by_type[entry.type].append(_item(entry))

    groups = tuple(
        BudgetGroup(
            type=group,
            items=tuple(by_type[group]),
            subtotal=sum((item.subtotal for item in by_type[group]), start=_ZERO),
        )
        for group in BUDGET_GROUPS
    )

    return Budget(
        groups=groups,
        total=sum((group.subtotal for group in groups), start=_ZERO),
        currency=CURRENCY,
        prices_as_of=min((entry.price_updated_at for entry in entries), default=None),
    )
