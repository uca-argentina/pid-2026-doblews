"""What the API says about the system catalogue: resources and recipes (HU-4)."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel


class UnitRef(BaseModel):
    """The unit something is measured in, as a label and not as a full catalogue row.

    code to compare, abbreviation to display. The rest of UnitOfMeasureOut stays
    behind GET /units-of-measure, which is what a "unidad" select is built from.
    """

    code: str
    abbreviation: str


class ResourceOut(BaseModel):
    """One row of the materials view.

    Decimal and not float, so the price reaches the frontend exactly as stored:
    Pydantic writes a Decimal to JSON as a string ("230.00").
    """

    id: int
    type: str
    name: str
    unit: UnitRef
    reference_price: Decimal
    currency: str
    # "Precios de referencia al <fecha>": how old the number is.
    price_updated_at: datetime


class RecipeLineOut(BaseModel):
    """One line of a recipe: this material, this much per one unit of the recipe.

    Carries the material's price so the expanded card can show what the line
    costs without the frontend cross-referencing the materials list.
    """

    resource_id: int
    name: str
    unit: UnitRef
    quantity_per_unit: Decimal
    reference_price: Decimal
    currency: str


class RecipeOut(BaseModel):
    """One recipe with everything it takes, as the catalogue browser renders it.

    The same shape HU-5's "Agregar" picker needs: the name and unit to choose it
    by, and the lines to tell two similar recipes apart before choosing.
    """

    id: int
    name: str
    description: str | None
    unit: UnitRef
    # "general" is the system catalogue, "firm" this firm's own (HU-9). What
    # the screens badge and filter by, and what decides whether a card offers
    # edit and deactivate at all.
    origin: Literal["general", "firm"]
    lines: list[RecipeLineOut]
