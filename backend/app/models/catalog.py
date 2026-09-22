"""The system catalogue: what a resource is, and what one unit of a recipe takes.

Global to the platform, not to any firm (ADR-003 section 1), so none of these three
tables carries firm_id and there is nothing to isolate in them. A recipe says what
*one* unit of something takes; how much of it a given work needs lives in
project_recipe, which is the only table of the five holding a firm's data.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# The three natures a resource can have, which is Presto's *naturaleza* column.
# Sprint 1 seeds only 'material': the other two exist in the CHECK and have no
# rows, so that adding labour and equipment to a recipe later is rows and not
# tables (ADR-003 section 3). VARCHAR + CHECK, never a native ENUM
# (modelo-datos 3.7).
RESOURCE_TYPE_CHECK = "type IN ('material', 'labor', 'equipment')"


class Resource(Base):
    """One input: a material today, a trade or a machine the day they are seeded.

    The price is a single reference price shared by every firm, and it is *live*:
    the take-off reads it at query time and never copies it (ADR-005 section 5).
    """

    __tablename__ = "resource"
    __table_args__ = (
        CheckConstraint(RESOURCE_TYPE_CHECK, name="type_valid"),
        # A price of zero is legitimate — something supplied by the client, say —
        # but a negative one is always a load error.
        CheckConstraint("reference_price >= 0", name="reference_price_not_negative"),
        # ISO 4217, three uppercase letters. The column exists and the conversion
        # logic does not: when a second currency shows up, historical rows already
        # say what they are expressed in (modelo-datos 3.5).
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_4217"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(150))

    # Chosen from the closed catalogue of HU-0, never free text.
    unit_of_measure_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unit_of_measure.id"))

    # NUMERIC, never float: a rounding error compounds across a whole budget
    # (modelo-datos 3.5).
    reference_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), server_default=text("'ARS'"))

    # Answers "how old is this price?", which the take-off screen has to show
    # ("precios de referencia al <fecha>", ADR-005 section 5). Not nullable: a
    # price with no date is a number the reader cannot judge. Deliberately not
    # updated_at — editing a resource's name must not move it.
    price_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recipe(Base):
    """What one unit of a building task takes. The APU of the trade.

    Its unit is the unit of *one* recipe: 1 m2 of a 15cm brick wall. There is no
    recipe inside a recipe — the decomposition is flattened on purpose
    (ADR-003 section 2).
    """

    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    name: Mapped[str] = mapped_column(String(150))
    # Where the assumptions behind the proportions are written down: the
    # thickness a per-m2 recipe implies, the mortar ratio it was computed from.
    description: Mapped[str | None] = mapped_column(Text)

    unit_of_measure_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("unit_of_measure.id"))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeResource(Base):
    """One line of a recipe: this resource, this much per unit. The yield.

    A pure link and not an entity, so it follows role_permission rather than the
    rest of the model: no is_active, no timestamps, and ON DELETE CASCADE. The
    team rule that nothing is ever physically deleted protects entities; editing
    a recipe in HU-8 means replacing its lines, and a line that survived its own
    removal as a tombstone would only have to be filtered out everywhere.
    """

    __tablename__ = "recipe_resource"
    __table_args__ = (
        # Zero would be a line that contributes nothing and reads as if it did.
        CheckConstraint("quantity_per_unit > 0", name="quantity_per_unit_positive"),
        # The other direction of the primary key: "which recipes use this
        # material?", which is the question ADR-005 section 6 asks before
        # allowing a resource to be deactivated.
        Index("ix_recipe_resource_resource_id", "resource_id"),
    )

    recipe_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recipe.id", ondelete="CASCADE"), primary_key=True
    )
    resource_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("resource.id", ondelete="CASCADE"), primary_key=True
    )

    # Four decimals and not two: a real yield is 0.0320 m3 of sand per m2, and
    # rounding that to 0.03 moves the take-off by 6%. Not money, so 3.5's
    # NUMERIC(14,2) does not apply.
    quantity_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4))


# Written outside the class bodies because a functional index needs the mapped
# column object, which __table_args__ is evaluated too early to have.
#
# Unique on lower(name) and only among the active rows (modelo-datos 3.4): the
# name of a resource is a label, not an identity. If "Cemento Loma Negra 50kg"
# was deactivated by mistake, nothing should stop it from being loaded again.
# The lower() is what keeps "Cemento" and "cemento" from coexisting. Unlike
# account.email there is no CHECK forcing lowercase storage, because this value
# is displayed as written.
Index(
    "uq_resource_name_active",
    func.lower(Resource.name),
    unique=True,
    postgresql_where=text("is_active"),
)
Index(
    "uq_recipe_name_active",
    func.lower(Recipe.name),
    unique=True,
    postgresql_where=text("is_active"),
)
