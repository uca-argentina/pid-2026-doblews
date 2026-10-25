"""Reaching a firm's purchase orders and their lines, and only those (ADR-011).

Both repositories start from FirmScopedRepository.select(), so a read already
carries firm_id = :firm and is_active before any method narrows it further. An
order of another firm, a discarded draft and an id that never existed are the
same None here, and the route answers all three with the same 404.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select

from app.models import (
    Account,
    Project,
    PurchaseOrder,
    PurchaseOrderLine,
    Resource,
    Supplier,
    UnitOfMeasure,
)
from app.repositories.base import FirmScopedRepository


@dataclass(frozen=True)
class OrderEntry:
    """An order with the names it is shown by: its work's and its supplier's."""

    order: PurchaseOrder
    project_name: str
    supplier_name: str


@dataclass(frozen=True)
class OrderLineEntry:
    """A line with the material it orders already looked up."""

    line: PurchaseOrderLine
    resource_name: str
    unit_code: str
    unit_abbreviation: str


class PurchaseOrderRepository(FirmScopedRepository[PurchaseOrder]):
    """This firm's live orders: every state, but no discarded draft."""

    model = PurchaseOrder

    def get(self, order_id: int) -> PurchaseOrder | None:
        return self.db.scalars(self.select().where(PurchaseOrder.id == order_id)).first()

    def _entries(self):
        return (
            self.select()
            .join(Project, Project.id == PurchaseOrder.project_id)
            .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
            .add_columns(Project.name, Supplier.name)
        )

    def entry(self, order_id: int) -> OrderEntry | None:
        row = self.db.execute(self._entries().where(PurchaseOrder.id == order_id)).first()
        return OrderEntry(*row) if row is not None else None

    def entries(self, order_ids: Collection[int]) -> list[OrderEntry]:
        """These orders, newest number first."""
        if not order_ids:
            return []
        rows = self.db.execute(
            self._entries()
            .where(PurchaseOrder.id.in_(order_ids))
            .order_by(PurchaseOrder.number.desc())
        ).all()
        return [OrderEntry(*row) for row in rows]

    def for_project(self, project_id: int, status: str | None = None) -> list[OrderEntry]:
        """A work's orders, newest number first, optionally of one status."""
        statement = self._entries().where(PurchaseOrder.project_id == project_id)
        if status is not None:
            statement = statement.where(PurchaseOrder.status == status)
        rows = self.db.execute(statement.order_by(PurchaseOrder.number.desc())).all()
        return [OrderEntry(*row) for row in rows]

    def for_firm(
        self,
        project_id: int | None = None,
        supplier_id: int | None = None,
        status: str | None = None,
    ) -> list[OrderEntry]:
        """Every order of the firm, newest number first, narrowed by what is given.

        The firm's listing (HU-21): the door through which an architect who is not
        on a work's team reaches its orders, so it does not filter by visibility.
        """
        statement = self._entries()
        if project_id is not None:
            statement = statement.where(PurchaseOrder.project_id == project_id)
        if supplier_id is not None:
            statement = statement.where(PurchaseOrder.supplier_id == supplier_id)
        if status is not None:
            statement = statement.where(PurchaseOrder.status == status)
        rows = self.db.execute(statement.order_by(PurchaseOrder.number.desc())).all()
        return [OrderEntry(*row) for row in rows]

    def account_names(self, account_ids: Collection[int]) -> dict[int, str]:
        """The names of the people an order's history mentions.

        Accounts are not a firm's rows, so this is a plain read by id: the ids
        come from an order that was already resolved under this firm.
        """
        if not account_ids:
            return {}
        rows = self.db.execute(
            select(Account.id, Account.name).where(Account.id.in_(account_ids))
        ).all()
        return {account_id: name for account_id, name in rows}

    def draft_for(self, project_id: int, supplier_id: int) -> PurchaseOrder | None:
        """The work's live draft to this supplier, if it has one.

        At most one, because generating and moving lines always reuse it
        (ADR-011 section 5): a work never has two drafts to the same supplier.
        """
        return self.db.scalars(
            self.select().where(
                PurchaseOrder.project_id == project_id,
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.status == "draft",
            )
        ).first()

    def highest_number(self) -> int:
        """The highest number this firm ever gave an order, discarded drafts included.

        Included on purpose: a discarded draft keeps its number, and a gap is
        never reused (ADR-011 section 4).
        """
        return (
            self.db.scalar(
                select(func.max(PurchaseOrder.number)).where(PurchaseOrder.firm_id == self.firm_id)
            )
            or 0
        )


class PurchaseOrderLineRepository(FirmScopedRepository[PurchaseOrderLine]):
    """This firm's live order lines."""

    model = PurchaseOrderLine

    def lines(self, order_ids: Collection[int]) -> dict[int, list[OrderLineEntry]]:
        """The live lines of these orders, by order, each list by material name."""
        if not order_ids:
            return {}
        rows = self.db.execute(
            self.select()
            .join(Resource, Resource.id == PurchaseOrderLine.resource_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
            .add_columns(Resource.name, UnitOfMeasure.code, UnitOfMeasure.abbreviation)
            .where(PurchaseOrderLine.purchase_order_id.in_(order_ids))
            .order_by(func.lower(Resource.name), PurchaseOrderLine.id)
        ).all()
        by_order: dict[int, list[OrderLineEntry]] = defaultdict(list)
        for row in rows:
            entry = OrderLineEntry(*row)
            by_order[entry.line.purchase_order_id].append(entry)
        return by_order

    def get(self, order_id: int, line_id: int) -> PurchaseOrderLine | None:
        """A live line of this order. Never reachable through an order it is not on."""
        return self.db.scalars(
            self.select().where(
                PurchaseOrderLine.purchase_order_id == order_id, PurchaseOrderLine.id == line_id
            )
        ).first()

    def for_resource(self, order_id: int, resource_id: int) -> PurchaseOrderLine | None:
        """The live line of this order for this material, if it has one."""
        return self.db.scalars(
            self.select().where(
                PurchaseOrderLine.purchase_order_id == order_id,
                PurchaseOrderLine.resource_id == resource_id,
            )
        ).first()

    def ordered_by_resource(self, project_id: int) -> dict[int, Decimal]:
        """How much of each material a work already has on order.

        Live lines of live orders that were not cancelled, drafts included: a
        draft is a purchase already being prepared, and counting it is what keeps
        "Generar órdenes" from asking twice for the same thing. A discarded draft
        or a cancelled order gives its quantity back.
        """
        rows = self.db.execute(
            select(PurchaseOrderLine.resource_id, func.sum(PurchaseOrderLine.quantity))
            .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.purchase_order_id)
            .where(
                PurchaseOrderLine.firm_id == self.firm_id,
                PurchaseOrderLine.is_active,
                PurchaseOrder.project_id == project_id,
                PurchaseOrder.is_active,
                PurchaseOrder.status != "cancelled",
            )
            .group_by(PurchaseOrderLine.resource_id)
        ).all()
        return {resource_id: quantity for resource_id, quantity in rows}
