"""A firm's suppliers, and the price list each one gives it (ADR-010).

Suppliers belong to the firm: a price is an agreement between that firm and that
supplier, so no other firm sees it. What a supplier prices is *not* theirs: it is
a material of the platform's catalogue (ADR-003), which is what makes one
corralón's list comparable with another's — both quote the same "Ladrillo común".

None of this feeds the budget. The take-off, HU-11 and HU-12 keep computing with
resource.reference_price; these two tables only feed the comparison of HU-18.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Supplier(Base):
    """One supplier of one firm: "Corralón Norte"."""

    __tablename__ = "supplier"
    __table_args__ = (
        # Target of supplier_price's composite FK: it is what proves a price row
        # hangs off a supplier that really belongs to that firm (modelo-datos 3.8).
        UniqueConstraint("id", "firm_id"),
        Index("ix_supplier_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # The tenant. Present in every query that reads this table (ADR-002 8).
    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("firm.id"))

    name: Mapped[str] = mapped_column(String(150))
    # All optional: a supplier is usable the moment it has a name.
    contact_name: Mapped[str | None] = mapped_column(String(120))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(String(255))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SupplierPrice(Base):
    """One row of a supplier's price list: this supplier sells this material at this price.

    An entity with its own id and logical deletion, and not a pure link like
    recipe_resource: rows are edited one at a time, a price changes far more often
    than a recipe's composition, and a row removed by mistake is loaded again
    without losing the previous one (ADR-010 section 2).
    """

    __tablename__ = "supplier_price"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="unit_price_not_negative"),
        CheckConstraint("shipping_cost >= 0", name="shipping_cost_not_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
        # The composite FK of modelo-datos 3.8: a price of another firm's supplier
        # is not refused by a service, it is impossible, because the pair has to
        # exist in supplier.
        ForeignKeyConstraint(
            ["supplier_id", "firm_id"],
            ["supplier.id", "supplier.firm_id"],
        ),
        # "Who sells this material?", the question the comparison of HU-18 asks.
        Index("ix_supplier_price_resource_id", "resource_id"),
        Index("ix_supplier_price_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    supplier_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant on purpose: the column the composite FK above shares with
    # supplier, and what lets the base repository filter by firm like any other
    # table (modelo-datos 3.2). The FK keeps it from ever diverging.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    # A material of the platform's catalogue. That it is a material and not labour
    # or equipment is a rule of the service and not of the schema (ADR-010 7).
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resource.id"))

    # Per ONE unit of the resource, in the unit the catalogue gives it. The
    # supplier does not pick another one (ADR-010 section 3).
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    # A fixed amount per material, whatever the quantity. Zero when the supplier
    # does not charge for delivery.
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'ARS'"))

    # Moves only when unit_price or shipping_cost change, like
    # resource.price_updated_at (ADR-005 section 5) and for the same reason: it is
    # the "actualizado el" the screen shows, and renaming nothing should touch it.
    price_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# Declared after the classes for the same reason as the catalogue's: the
# functional expression needs the column object, which __table_args__ is
# evaluated too early to have.
#
# Unique on lower(name) among the firm's active suppliers (modelo-datos 3.4): a
# name is a label and not an identity, so a supplier deactivated by mistake can be
# loaded again, and "Corralón Norte" cannot coexist with "corralón norte".
Index(
    "uq_supplier_name_active",
    Supplier.firm_id,
    func.lower(Supplier.name),
    unique=True,
    postgresql_where=text("is_active"),
)
# A supplier does not repeat a material in its list. Partial, so a row removed by
# mistake is loaded again as a new one.
Index(
    "uq_supplier_price_resource_active",
    SupplierPrice.supplier_id,
    SupplierPrice.resource_id,
    unique=True,
    postgresql_where=text("is_active"),
)
