"""What support's admin screens send to write the system catalogue (HU-8).

The read side — ResourceOut, RecipeOut and the rest of what a firm member sees
— stays in app.schemas.catalog: the admin screens show support the same shape
HU-4 shows everyone else, since it is the same catalogue. Only the write forms
live here, because HU-4 has none.
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints, field_validator

# Same width as resource.name and recipe.name (String(150)). Stripped, so "   "
# is empty and refused.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]

# The limits of resource.reference_price, NUMERIC(14,2) and CHECK >= 0 (zero is
# a legitimate price — something the client supplies — a negative one is not).
Price = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]

# The limits of recipe_resource.quantity_per_unit, NUMERIC(12,4) and CHECK > 0.
QuantityPerUnit = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=4)]

# Mirrors resource's CHECK constraint (app.models.catalog.RESOURCE_TYPE_CHECK), so
# a bad value is a 422 naming the field instead of an IntegrityError surfacing as
# a 500. Sprint 1 only seeds 'material'; the other two exist for the day the team
# decides to load them (ADR-003 section 3).
ResourceType = Literal["material", "labor", "equipment"]


def _blank_to_none(value: object) -> object:
    """An empty description field is no description, not one made of nothing."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


Description = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True)] | None,
    BeforeValidator(_blank_to_none),
]


class ResourceWrite(BaseModel):
    """The create and edit form for one resource: name, type, unit and price.

    A full replace, like HU-3's ProjectWrite: editing sends every field again,
    not a patch. unit_of_measure_id is chosen from GET /units-of-measure, the
    closed catalogue HU-0 defines — never free text.
    """

    name: Name
    type: ResourceType
    unit_of_measure_id: int
    reference_price: Price


class RecipeLineWrite(BaseModel):
    """One line of the master-detail form: this material, this much per unit."""

    resource_id: int
    quantity_per_unit: QuantityPerUnit


class RecipeWrite(BaseModel):
    """The create and edit form for one recipe: its header and every one of its lines.

    lines demands at least one row (ADR-005 section 7.2): a recipe with none
    would save, compute zero materials in every take-off that used it, and no
    error would ever say why. Editing replaces the whole set, like the lines
    array itself: there is no per-line PATCH, only "this is the recipe now."
    """

    name: Name
    description: Description = None
    unit_of_measure_id: int
    lines: Annotated[list[RecipeLineWrite], Field(min_length=1)]

    @field_validator("lines")
    @classmethod
    def no_repeated_resource(cls, lines: list[RecipeLineWrite]) -> list[RecipeLineWrite]:
        resource_ids = [line.resource_id for line in lines]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("un material no puede repetirse en la misma receta")
        return lines
