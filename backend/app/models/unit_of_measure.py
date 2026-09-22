"""The unit of measure catalogue: global to the platform, seeded by migration.

Knows nothing about firms or projects. A table and not a VARCHAR + CHECK
enumerated column (modelo-datos 3.7) because it carries its own abbreviation and
magnitude alongside the code.
"""

from sqlalchemy import BigInteger, Boolean, Identity, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UnitOfMeasure(Base):
    """One measurement unit (m2, kg, bolsa, ...), read-only at runtime."""

    __tablename__ = "unit_of_measure"
    __table_args__ = (UniqueConstraint("code"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # Stable identifier used in seeds and joins, e.g. "m2".
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(60))
    # What a select actually shows next to a value, e.g. "m2".
    abbreviation: Mapped[str] = mapped_column(String(10))
    # Grouping label, e.g. "superficie" or "volumen". Not exposed by ADR-003's
    # own AC list, kept for a future select that groups or filters by it.
    magnitude: Mapped[str] = mapped_column(String(30))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
