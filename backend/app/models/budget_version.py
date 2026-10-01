"""A frozen budget of one work, and the two tables that make it up (ADR-007).

The draft — project_recipe plus the query of ADR-003 section 2 — keeps reading
the live price and the live recipe. These three tables are a second artefact
beside it: what the budget said the day someone decided to keep it, which no
later price correction or retired recipe may move.

Nothing here carries is_active or updated_at. A version is never edited and
never deactivated (HU-12 leaves deleting versions out of scope), so the
updated_at trigger of modelo-datos 3.11 does not apply — the first tables in the
project where it does not, in the same spirit that recipe_resource already omits
timestamps for being a pure link.
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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.catalog import RESOURCE_TYPE_CHECK

# The same three natures as resource.type, re-stated against this table's own
# column name. Copied and not referenced, like every other field of an item.
ITEM_TYPE_CHECK = RESOURCE_TYPE_CHECK.replace("type IN", "resource_type IN")


class BudgetVersion(Base):
    """One saved budget of a work: "v3 — Presentado al cliente 20/10"."""

    __tablename__ = "budget_version"
    __table_args__ = (
        # v0 is not a version, and the service counts from 1.
        CheckConstraint("version_number > 0", name="version_number_positive"),
        # A budget of zero is legitimate — nothing priced yet is refused earlier,
        # by the "no empty take-off" rule — but a negative one is a bug.
        CheckConstraint("total >= 0", name="total_not_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
        # Correlative per work, which is what HU-12 asks for. The schema sets the
        # floor here; which number is next is the service's call, under the lock
        # described in ADR-007 section 3.
        UniqueConstraint("project_id", "version_number"),
        # The composite FK of modelo-datos 3.8, the same mechanism project_recipe
        # uses. A version of another firm's work is not refused by a service: it
        # is impossible, because the pair has to exist in project.
        ForeignKeyConstraint(
            ["project_id", "firm_id"],
            ["project.id", "project.firm_id"],
        ),
        # The listing of one work's versions, newest first.
        Index("ix_budget_version_project_id", "project_id"),
        Index("ix_budget_version_firm_id", "firm_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    project_id: Mapped[int] = mapped_column(BigInteger)
    # Redundant on purpose: the column the composite FK above shares with
    # project, which is what ties this version to that work's firm.
    firm_id: Mapped[int] = mapped_column(BigInteger)

    # Correlative within the work: v1, v2, v3. Never global — a global sequence
    # would let one firm infer how many versions another saves, from the gaps in
    # its own numbering (ADR-007, alternatives).
    version_number: Mapped[int] = mapped_column(Integer)

    # Name and note are one field: "Presentado al cliente 20/10" is both.
    note: Mapped[str | None] = mapped_column(String(150))

    # The sum of the subtotals as they were shown, so a version reprints exactly
    # what was presented rather than something recomputed from its items.
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'ARS'"))

    # The oldest price this version was built from, frozen with it: the detail
    # screen says "precios de referencia al <fecha>" with this and not with
    # today's (ADR-005 section 5, and ADR-007 consequences).
    prices_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("account.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BudgetVersionItem(Base):
    """One resource of a saved budget, with the numbers it had that day.

    Everything here is copied, resource_id included, and that one deliberately
    travels without a foreign key: the point of a frozen item is that it does
    not need anything else to still exist in order to be shown. It is a receipt,
    not a view over live data. The id stays as information — a future "ver este
    material hoy" link — and the row's integrity does not depend on it.
    """

    __tablename__ = "budget_version_item"
    __table_args__ = (
        CheckConstraint(ITEM_TYPE_CHECK, name="resource_type_valid"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price >= 0", name="unit_price_not_negative"),
        CheckConstraint("subtotal >= 0", name="subtotal_not_negative"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
        Index("ix_budget_version_item_budget_version_id", "budget_version_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # ON DELETE CASCADE, against the general rule that a foreign key to business
    # data never cascades (modelo-datos 3.3). That rule is about entities, and an
    # item is not one: it is pure composition of the same aggregate, the category
    # recipe_resource already occupies with respect to recipe.
    budget_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("budget_version.id", ondelete="CASCADE")
    )

    # Informational, without a foreign key. See the class docstring.
    resource_id: Mapped[int] = mapped_column(BigInteger)
    resource_name: Mapped[str] = mapped_column(String(150))
    resource_type: Mapped[str] = mapped_column(String(20))
    # The abbreviation and not the unit's id, for the same reason: the row has
    # to render with no join at all.
    unit_abbreviation: Mapped[str] = mapped_column(String(10))

    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'ARS'"))
    # Stored and not computed: it is the already rounded amount that was on
    # screen, and recomputing quantity x unit_price would round a second time.
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class BudgetVersionLine(Base):
    """One take-off line as it stood when the version was saved.

    The opposite job to an item, which is why it is a second table. An item
    exists to *show* numbers and groups by resource; a line exists to *rebuild*
    the draft when someone loads the version, and is one row per take-off entry —
    two walls measured per storey come back as two lines with their notes, not
    fused into one.

    recipe_id is a real foreign key, and live on purpose: loading a version has
    to know whether that recipe is still active today, because HU-12 says a
    retired one is left out and reported.
    """

    __tablename__ = "budget_version_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_budget_version_line_budget_version_id", "budget_version_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    budget_version_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("budget_version.id", ondelete="CASCADE")
    )

    recipe_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("recipe.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    note: Mapped[str | None] = mapped_column(String(150))
