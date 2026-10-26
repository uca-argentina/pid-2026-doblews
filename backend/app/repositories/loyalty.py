"""Reading a firm's points entries, and only that firm's (ADR-012 section 4).

Not a FirmScopedRepository, for the same reason BudgetVersionRepository is not:
the base class refuses any model without both firm_id and is_active, and an
entry carries no is_active — it is never deactivated, because an order that was
received is never reopened. The firm is pinned by hand instead, in the one
select every read here starts from, so the guarantee is the same even though the
mechanism is not.

Nothing here writes. The entries are added by services/loyalty.py, which is also
where the rule that produced them lives.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session

from app.models import (
    FirmPointsEntry,
    Project,
    PurchaseOrder,
    Resource,
    Supplier,
    UnitOfMeasure,
)


@dataclass(frozen=True)
class PointsHistoryEntry:
    """One entry as the history reads it, with every name already looked up.

    The history has to explain each number: which order earned it, for which
    work, from which supplier and on what material (ADR-012 section 7).
    """

    id: int
    earned_at: datetime
    points: int
    rule: str
    quantity: Decimal
    previous_quantity: Decimal | None
    order_id: int
    order_number: int
    project_id: int
    project_name: str
    supplier_id: int
    supplier_name: str
    resource_id: int
    resource_name: str
    unit_code: str
    unit_abbreviation: str


class FirmPointsEntryRepository:
    """Every read starts from the base select, so it is this firm's rows only."""

    def __init__(self, db: Session, firm_id: int) -> None:
        self.db = db
        self.firm_id = firm_id

    def select(self) -> Select:
        """This firm's entries, and nothing else. No is_active: there is none."""
        return select(FirmPointsEntry).where(FirmPointsEntry.firm_id == self.firm_id)

    def rated(self, order_id: int) -> bool:
        """Whether this order already earned its points.

        What keeps awarding idempotent above the unique index, so a second call
        is a no-op instead of an IntegrityError the caller has to read.
        """
        return bool(
            self.db.scalar(
                select(
                    exists().where(
                        FirmPointsEntry.firm_id == self.firm_id,
                        FirmPointsEntry.purchase_order_id == order_id,
                    )
                )
            )
        )

    def total(self) -> int:
        """Every point this firm has earned. Zero while it has earned none.

        The firm's level is this sum and not a column (ADR-012 section 4): there
        is no running total to keep coherent, and the index on firm_id is what
        makes asking cheap.
        """
        return self.db.scalar(
            select(func.coalesce(func.sum(FirmPointsEntry.points), 0)).where(
                FirmPointsEntry.firm_id == self.firm_id
            )
        )

    def total_with(self, supplier_id: int) -> int:
        """What this firm has earned with one supplier: its level with them."""
        return self.db.scalar(
            select(func.coalesce(func.sum(FirmPointsEntry.points), 0)).where(
                FirmPointsEntry.firm_id == self.firm_id,
                FirmPointsEntry.supplier_id == supplier_id,
            )
        )

    def history(self) -> list[PointsHistoryEntry]:
        """Every entry of this firm, newest first.

        By id and not by created_at: entries written in one transaction share a
        timestamp, and the id is the order they were really written in.

        Whole and unpaged, like the firm's order listing of HU-21: a studio's
        received orders are few, and the screen filters what it has.
        """
        rows = self.db.execute(
            self.select()
            .join(PurchaseOrder, PurchaseOrder.id == FirmPointsEntry.purchase_order_id)
            .join(Project, Project.id == PurchaseOrder.project_id)
            .join(Supplier, Supplier.id == FirmPointsEntry.supplier_id)
            .join(Resource, Resource.id == FirmPointsEntry.resource_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
            .add_columns(
                PurchaseOrder.number,
                Project.id,
                Project.name,
                Supplier.name,
                Resource.name,
                UnitOfMeasure.code,
                UnitOfMeasure.abbreviation,
            )
            .order_by(FirmPointsEntry.id.desc())
        ).all()
        return [
            PointsHistoryEntry(
                id=entry.id,
                earned_at=entry.created_at,
                points=entry.points,
                rule=entry.rule,
                quantity=entry.quantity,
                previous_quantity=entry.previous_quantity,
                order_id=entry.purchase_order_id,
                order_number=number,
                project_id=project_id,
                project_name=project_name,
                supplier_id=entry.supplier_id,
                supplier_name=supplier_name,
                resource_id=entry.resource_id,
                resource_name=resource_name,
                unit_code=unit_code,
                unit_abbreviation=unit_abbreviation,
            )
            for (
                entry,
                number,
                project_id,
                project_name,
                supplier_name,
                resource_name,
                unit_code,
                unit_abbreviation,
            ) in rows
        ]
