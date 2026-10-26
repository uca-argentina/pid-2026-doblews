"""A firm's purchase orders to its suppliers, for one of its works (ADR-011).

An order is born from HU-18's comparison: the cheapest supplier of each material,
at the quantity the work still needs. What it adds over the comparison is
commitment — the price and the shipping are copied when the line is made and
stay as they were, whatever the supplier's list says later (ADR-011 section 2).

The receipts of ADR-011 section 1 are the last two tables here (HU-22): what
arrived of a line on a day, and what was paid for it. The columns that only make
sense once an order is issued, cancelled or received were there from the first
migration, so the status and its dates are pinned by the schema rather than by
whichever story got around to writing them.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# The five states of ADR-011 section 3. VARCHAR + CHECK, never a native ENUM, like
# project_task.status (ADR-009 section 5). The two received ones are never chosen:
# the service derives them from the receipts.
ORDER_STATUS_CHECK = "status IN ('draft', 'issued', 'partially_received', 'received', 'cancelled')"


class PurchaseOrder(Base):
    """One order to one supplier, for one work: "OC-0007, Corralón Norte, Casa Rodríguez"."""

    __tablename__ = "purchase_order"
    __table_args__ = (
        CheckConstraint(ORDER_STATUS_CHECK, name="status_valid"),
        CheckConstraint("number > 0", name="number_positive"),
        # The dates say what the status says, so neither can be written without the
        # other. A draft was never issued; anything past issued was; a cancelled
        # order may or may not have been, which is why it is left out of both.
        CheckConstraint("status <> 'draft' OR issued_at IS NULL", name="draft_not_issued"),
        CheckConstraint(
            "status NOT IN ('issued', 'partially_received', 'received') OR issued_at IS NOT NULL",
            name="issued_has_date",
        ),
        CheckConstraint("(issued_at IS NULL) = (issued_by IS NULL)", name="issued_by_with_date"),
        CheckConstraint(
            "(status = 'cancelled') = (cancelled_at IS NOT NULL)", name="cancelled_has_date"
        ),
        CheckConstraint(
            "(cancelled_at IS NULL) = (cancelled_by IS NULL)", name="cancelled_by_with_date"
        ),
        CheckConstraint(
            "(status = 'received') = (received_at IS NOT NULL)", name="received_has_date"
        ),
        # Correlative per firm (ADR-011 section 4): OC-0001 is one order in the
        # whole firm, read the same from the work and from the firm's listing.
        UniqueConstraint("firm_id", "number"),
        # Target of purchase_order_line's composite FK.
        UniqueConstraint("id", "firm_id"),
        # The work and the supplier are the firm's own, by construction: the pairs
        # have to exist in project and in supplier (modelo-datos 3.8).
        ForeignKeyConstraint(["project_id", "firm_id"], ["project.id", "project.firm_id"]),
        ForeignKeyConstraint(["supplier_id", "firm_id"], ["supplier.id", "supplier.firm_id"]),
        Index("ix_purchase_order_firm_id", "firm_id"),
        Index("ix_purchase_order_project_id", "project_id"),
        Index("ix_purchase_order_supplier_id", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # The tenant. Present in every query that reads this table (ADR-002 8).
    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("firm.id"))
    project_id: Mapped[int] = mapped_column(BigInteger)
    supplier_id: Mapped[int] = mapped_column(BigInteger)

    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), server_default=text("'draft'"))

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("account.id"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("account.id"))
    # When the last receipt completed it: what HU-23 orders "the previous purchase" by.
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Discarding a draft, which is not cancelling it: a discarded draft never
    # existed for anyone and leaves every listing (ADR-011 section 1).
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # updated_at is kept by a database trigger, not the ORM (modelo-datos 3.11).
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderLine(Base):
    """One line of an order: this material, this much, at the price it had that day."""

    __tablename__ = "purchase_order_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_not_negative"),
        CheckConstraint("shipping_cost >= 0", name="shipping_cost_not_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
        ForeignKeyConstraint(
            ["purchase_order_id", "firm_id"],
            ["purchase_order.id", "purchase_order.firm_id"],
        ),
        Index("ix_purchase_order_line_purchase_order_id", "purchase_order_id"),
        Index("ix_purchase_order_line_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    purchase_order_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant on purpose, like supplier_price.firm_id: what lets the base
    # repository filter by firm. The composite FK keeps it from diverging.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    # Referenced, not copied: the catalogue deactivates and never deletes, so the
    # name and the unit are always there to show (ADR-011 section 2).
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resource.id"))

    # The scale of the take-off, so HU-18's quantity enters as it is.
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    # Copied from the supplier's list when the line is made, and frozen there: an
    # order is a commitment to a price (ADR-011 section 2).
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    shipping_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'ARS'"))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# An order does not repeat a material. Partial, so a line removed from a draft can
# be added again as a new one.
Index(
    "uq_purchase_order_line_resource_active",
    PurchaseOrderLine.purchase_order_id,
    PurchaseOrderLine.resource_id,
    unique=True,
    postgresql_where=text("is_active"),
)


class PurchaseOrderReceipt(Base):
    """One delivery of an order: what arrived on a day, and what it was paid for."""

    __tablename__ = "purchase_order_receipt"
    __table_args__ = (
        # The freight of this delivery, which a remito charges once for the whole
        # truck and not per material (ADR-011 section 8). NULL is "none charged",
        # which is not the same as zero: the supplier may simply not have said.
        CheckConstraint(
            "shipping_cost IS NULL OR shipping_cost >= 0", name="shipping_cost_not_negative"
        ),
        ForeignKeyConstraint(
            ["purchase_order_id", "firm_id"],
            ["purchase_order.id", "purchase_order.firm_id"],
        ),
        Index("ix_purchase_order_receipt_purchase_order_id", "purchase_order_id"),
        Index("ix_purchase_order_receipt_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    purchase_order_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant with its order's, like the line's: the composite FK above keeps the
    # two from diverging, and it is what the repository narrows every read by.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    # The day the delivery arrived, in Argentina (core/clock.py). A date and not a
    # timestamp, because a remito is dated by the day.
    received_on: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(150))

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"))
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    # The one correction an order allows: cancelling its last receipt (ADR-011
    # section 3). A cancelled receipt stops counting towards everything derived.
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseOrderReceiptLine(Base):
    """How much of one line arrived in one delivery, and what was paid for it.

    Pure composition of its receipt, the way budget_version_item is of its version
    (ADR-007 section 1): no firm_id and no is_active of
    its own, because it is only ever reached through receipt_id — already tied to a
    firm — and it goes out of use with the receipt that holds it.
    """

    __tablename__ = "purchase_order_receipt_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("actual_cost >= 0", name="actual_cost_not_negative"),
        # A line appears once per delivery: two rows for the same one would be the
        # same material arriving twice in a single delivery.
        #
        # Named by hand, against the convention: uq_<table>_<columns> would come
        # to 64 characters here and Postgres keeps 63, so the name would reach
        # the database truncated with a hash on the end and nothing could refer
        # to it by the name it was written with.
        UniqueConstraint(
            "receipt_id",
            "purchase_order_line_id",
            name="uq_purchase_order_receipt_line_once",
        ),
        Index("ix_purchase_order_receipt_line_receipt_id", "receipt_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    receipt_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("purchase_order_receipt.id"))
    purchase_order_line_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("purchase_order_line.id")
    )

    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    # What the invoice charged for this material in this delivery, freight aside:
    # the receipt carries that once (ADR-011 section 8). An amount and not a unit
    # price, because what the architect has in hand is the remito, not a division.
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
