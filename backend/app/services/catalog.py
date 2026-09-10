"""Reads over the platform's read-only catalogues (ADR-003)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import UnitOfMeasure


def list_units_of_measure(db: Session) -> list[UnitOfMeasure]:
    """The active units of measure, ordered by code.

    No firm/project filter: the catalogue is global to the platform
    (ADR-003 section 7), so every caller sees the same rows.
    """
    return list(
        db.scalars(
            select(UnitOfMeasure).where(UnitOfMeasure.is_active).order_by(UnitOfMeasure.code)
        )
    )
