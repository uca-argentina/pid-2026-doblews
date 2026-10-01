"""What the API says about a work's saved budget versions (HU-12).

The detail reuses the three-group shape of HU-11, so the same screen renders a
version and the draft. It is not the same schema, though, and the difference is
the point: a frozen item carries its unit as the abbreviation it was saved with,
not a reference to the unit catalogue, because a receipt must render even if
that unit row changed since.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, StringConstraints, field_validator

from app.schemas.catalog_admin import ResourceType

# Same limit as a take-off line's note: it is the same kind of label, written in
# the same kind of box.
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]


class BudgetVersionCreate(BaseModel):
    """The save form: a name or note, and nothing else.

    Nothing about the numbers is sent. What gets frozen is what the server
    computes at that moment — a client that could propose its own totals would
    be a client that could propose the wrong ones.
    """

    note: Note | None = None

    @field_validator("note")
    @classmethod
    def blank_is_no_note(cls, note: str | None) -> str | None:
        # Same normalisation as a take-off line: "   " is not a label.
        return note or None


class BudgetVersionSummary(BaseModel):
    """One row of the versions listing: enough to choose one, not to read it."""

    id: int
    version_number: int
    note: str | None
    total: Decimal
    currency: str
    created_at: datetime
    created_by_name: str


class BudgetVersionItemOut(BaseModel):
    """One frozen resource: the numbers exactly as they were saved."""

    resource_id: int
    name: str
    # The abbreviation as saved, not a UnitRef: see the module docstring.
    unit_abbreviation: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal


class BudgetVersionGroupOut(BaseModel):
    """One of the three groups of a saved version.

    The three always travel, empty ones included, exactly like the draft's, so
    the frontend renders both through one component.
    """

    type: ResourceType
    items: list[BudgetVersionItemOut]
    subtotal: Decimal


class BudgetVersionLineOut(BaseModel):
    """One take-off line as it stood when the version was saved.

    Shown so a reader can see what was measured, not only what it cost. The
    recipe name is read live: the line keeps a real reference to it, and a
    renamed recipe is still the same recipe.
    """

    recipe_id: int
    recipe_name: str
    quantity: Decimal
    note: str | None


class BudgetVersionOut(BaseModel):
    """A saved version in full, read-only.

    total is the stored number and not a sum recomputed from the items: it is
    what was on screen the day it was agreed, and recomputing it would quietly
    turn a record into a derivation.
    """

    id: int
    version_number: int
    note: str | None
    groups: list[BudgetVersionGroupOut]
    lines: list[BudgetVersionLineOut]
    total: Decimal
    currency: str
    # Frozen with the version: "precios de referencia al <fecha>" here says when
    # those prices were current, which is not today (ADR-005 section 5).
    prices_as_of: datetime
    created_at: datetime
    created_by_name: str


class BudgetVersionLoadOut(BaseModel):
    """What loading a version actually did.

    skipped is never hidden behind a flag: HU-12 asks the screen to say which
    lines were left out, so the names travel even when the list is empty.
    """

    loaded: int
    skipped: list[str]
