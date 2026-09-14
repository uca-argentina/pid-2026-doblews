"""What the API says about a work's take-off, and what it accepts to change it (HU-5).
The shapes HU-5's screen reads and its add and edit forms send; the cost fields are
nullable because a caller without project.cost.view gets them empty.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.schemas.catalog import UnitRef

# The limits of project_recipe.quantity, NUMERIC(14,3) and CHECK > 0, so a bad
# quantity is a 422 naming the field rather than a DataError surfacing as a 500.
Quantity = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=3)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, max_length=150)]


class _NoteField(BaseModel):
    """The optional label both forms share, with a blank normalised to no note."""

    note: Note | None = None

    @field_validator("note")
    @classmethod
    def blank_is_no_note(cls, note: str | None) -> str | None:
        # "   " stripped is "", and an empty label is not a label: stored as NULL
        # so the listing never tells two lines apart by an invisible note.
        return note or None


class TakeoffLineCreate(_NoteField):
    """The add form: which recipe, how much of it, and optionally where.

    The recipe is chosen from GET /catalog/recipes, so the frontend already holds
    its id. The quantity is in the recipe's own unit — 120 means 120 m2 of a
    per-m2 wall — and there is no unit field to disagree with it.
    """

    recipe_id: int
    quantity: Quantity


class TakeoffLineUpdate(_NoteField):
    """The edit form: the quantity and the note, both sent every time (a PUT).

    A separate schema from the add form, unlike HU-3's single ProjectWrite,
    because the recipe is deliberately not editable: changing it would change the
    unit the quantity is expressed in. Without recipe_id here, a body that sends
    one is simply not read.
    """

    quantity: Quantity


class RecipeRef(BaseModel):
    """The recipe a line measures: enough to render it, not the full catalogue card."""

    id: int
    name: str
    unit: UnitRef


class TakeoffLineOut(BaseModel):
    """One line of the take-off, as the listing shows it and a write answers with."""

    id: int
    recipe: RecipeRef
    quantity: Decimal
    note: str | None


class TakeoffMaterialOut(BaseModel):
    """One material the work needs, summed across every line.

    cost is null when the caller may not see costs. The field stays, so the
    frontend reads one shape and only asks whether the value is there.
    """

    resource_id: int
    name: str
    unit: UnitRef
    quantity: Decimal
    cost: Decimal | None
    currency: str


class TakeoffOut(BaseModel):
    """A work's whole take-off in one answer: its lines and what they add up to.

    One response and not two, so the lines and the totals on screen always come
    from the same moment and cannot disagree after a write.
    """

    lines: list[TakeoffLineOut]
    materials: list[TakeoffMaterialOut]
    # The sum of the materials' costs as shown, so the column adds up exactly.
    # "0.00" for an empty take-off; null when the caller may not see costs.
    total_cost: Decimal | None
    currency: str
    # "Precios de referencia al <fecha>" (ADR-005 section 5): the oldest price
    # the total is built from. null when there is nothing to price.
    prices_as_of: datetime | None
