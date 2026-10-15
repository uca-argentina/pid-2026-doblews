"""What the API says and accepts about suppliers and their price lists (HU-17, ADR-010)."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.schemas.catalog import UnitRef

# Same width as supplier.name (String(150)). Stripped, so "   " is empty and refused.
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]

# The limits of supplier_price.unit_price and shipping_cost: NUMERIC(14,2) with
# CHECK >= 0. Zero is legitimate — a free delivery — a negative one is not.
Amount = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


def _blank_to_none(value: object) -> object:
    """An empty optional field is no value, not one made of nothing."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _optional_text(max_length: int):
    return Annotated[
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=max_length)] | None,
        BeforeValidator(_blank_to_none),
    ]


ContactName = _optional_text(120)
Phone = _optional_text(30)
Address = _optional_text(255)
# EmailStr already caps the address at 254 characters (RFC 5321), inside the column's 255.
ContactEmail = Annotated[EmailStr | None, BeforeValidator(_blank_to_none)]


class SupplierCreate(BaseModel):
    """The create form: a name, and whatever else the architect knows."""

    name: Name
    contact_name: ContactName = None
    contact_email: ContactEmail = None
    phone: Phone = None
    address: Address = None


class SupplierUpdate(BaseModel):
    """The edit form: only what changed (PATCH, ADR-010 section 8).

    Sending a field as null clears it, except the name, which is required. The
    route tells "not sent" from "sent as null" with model_fields_set.
    """

    name: Name | None = None
    contact_name: ContactName = None
    contact_email: ContactEmail = None
    phone: Phone = None
    address: Address = None

    @field_validator("name")
    @classmethod
    def name_is_required(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("el nombre es obligatorio")
        return value


class SupplierOut(BaseModel):
    """One supplier of the listing, with how long its price list is."""

    id: int
    name: str
    contact_name: str | None
    contact_email: str | None
    phone: str | None
    address: str | None
    price_count: int


class SupplierPriceCreate(BaseModel):
    """Add a material to a supplier's list: which one, at what price, with what shipping."""

    resource_id: int
    unit_price: Amount
    shipping_cost: Amount = Decimal("0.00")


class SupplierPriceUpdate(BaseModel):
    """Change a row's amounts. The material is not editable: to price another one,
    remove this row and add the other (the row is identified by its material)."""

    unit_price: Amount | None = None
    shipping_cost: Amount | None = None

    @field_validator("unit_price", "shipping_cost")
    @classmethod
    def amount_is_required(cls, value: Decimal | None) -> Decimal:
        if value is None:
            raise ValueError("el importe no puede ser nulo")
        return value


class PricedResource(BaseModel):
    """The material a row prices, as the list shows it."""

    id: int
    name: str
    unit: UnitRef
    # The price the budget computes with. Shown beside the supplier's so the
    # screen can always say which of the two it is looking at (ADR-010 section 5).
    reference_price: Decimal


class SupplierPriceOut(BaseModel):
    """One row of a supplier's price list."""

    id: int
    resource: PricedResource
    unit_price: Decimal
    shipping_cost: Decimal
    currency: str
    # "Actualizado el <fecha>": moves only when an amount changes.
    price_updated_at: datetime


class SupplierDetailOut(SupplierOut):
    """A supplier with its whole price list."""

    prices: list[SupplierPriceOut]
