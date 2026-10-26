"""The points a firm earns for buying from a supplier again (ADR-012).

One row per order line that earned points, written once when the order became
received and never touched afterwards. The firm's level is not a column
anywhere: it is the sum of these rows, computed on every read (ADR-012 section
4), so there is no derived value to keep coherent.

Immutable, like budget_version and its items (ADR-007 section 1): no is_active,
because nothing deactivates an entry — an order that was received is never
reopened — and no updated_at, because nothing updates one. A points system that
rewrote its own past could not explain a number with the rule that earned it.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# The four cases of ADR-012 section 3, in the order they are tried. VARCHAR +
# CHECK and never a native ENUM, like every other status in the project.
POINTS_RULES = (
    "same_material_similar_quantity",
    "same_material",
    "same_supplier",
    "first_purchase",
)

RULE_CHECK = "rule IN (" + ", ".join(f"'{rule}'" for rule in POINTS_RULES) + ")"


class FirmPointsEntry(Base):
    """Why one line of one order earned what it earned: the receipt of a point."""

    __tablename__ = "firm_points_entry"
    __table_args__ = (
        CheckConstraint(RULE_CHECK, name="rule_valid"),
        # Points are only ever added (ADR-012: restar puntos is out of scope),
        # and first_purchase legitimately earns zero.
        CheckConstraint("points >= 0", name="points_not_negative"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint(
            "previous_quantity IS NULL OR previous_quantity > 0",
            name="previous_quantity_positive",
        ),
        # A line earns once. The service also refuses to award an order twice,
        # but this is what makes it true however it is called.
        UniqueConstraint("purchase_order_line_id"),
        # The supplier is the firm's own, by construction (ADR-010 left
        # supplier with UNIQUE (id, firm_id) for exactly this).
        ForeignKeyConstraint(["supplier_id", "firm_id"], ["supplier.id", "supplier.firm_id"]),
        # The two sums HU-24 reads: the firm's points, and the firm's with one
        # supplier.
        Index("ix_firm_points_entry_firm_id", "firm_id"),
        Index("ix_firm_points_entry_firm_id_supplier_id", "firm_id", "supplier_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # The tenant. The points belong to the firm and not to whoever bought: the
    # relationship with a supplier is the studio's (ADR-012 section 1).
    firm_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("firm.id"))
    supplier_id: Mapped[int] = mapped_column(BigInteger)

    purchase_order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("purchase_order.id"))
    purchase_order_line_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("purchase_order_line.id")
    )
    # Referenced and not copied, like the order line's own: the catalogue
    # deactivates and never deletes, so the name is always there to show.
    resource_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resource.id"))

    # Which of the four cases applied, and what it was worth that day. Stored
    # and never recomputed: changing a value tomorrow does not move what was
    # already earned (ADR-012 section 4).
    rule: Mapped[str] = mapped_column(String(40))
    points: Mapped[int] = mapped_column(Integer)

    # What was received of this material, and what it was compared against, so
    # the history can say "como la vez pasada (1.000 u)". NULL when there was
    # nothing to compare: a material never bought from this supplier, or the
    # firm's first order to it.
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    previous_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 3))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
