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

from sqlalchemy import Select, exists, select
from sqlalchemy.orm import Session

from app.models import FirmPointsEntry


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
