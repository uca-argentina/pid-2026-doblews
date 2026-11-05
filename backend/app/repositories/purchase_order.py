"""Reaching a firm's purchase orders, their lines and their receipts (ADR-011).

The three repositories start from FirmScopedRepository.select(), so a read already
carries firm_id = :firm and is_active before any method narrows it further. An
order of another firm, a discarded draft and an id that never existed are the
same None here, and the route answers all three with the same 404.
"""

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import exists, func, select

from app.models import (
    Account,
    Project,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderReceipt,
    PurchaseOrderReceiptLine,
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

    def received_from(self, supplier_id: int, *, besides: int) -> bool:
        """Whether this firm ever completed another order from this supplier.

        What separates the two zero-history cases of ADR-012 section 3: a firm
        that never bought from them (first_purchase) from one that buys often
        and never bought this material (same_supplier). `besides` leaves out the
        order being rated, which has just become received itself.
        """
        return bool(
            self.db.scalar(
                select(
                    exists(
                        self.select().where(
                            PurchaseOrder.supplier_id == supplier_id,
                            PurchaseOrder.status == "received",
                            PurchaseOrder.id != besides,
                        )
                    )
                )
            )
        )

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

    def last_received_quantities(self, supplier_id: int, *, besides: int) -> dict[int, Decimal]:
        """Per material, how much of it came the last time it was bought here.

        "The last time" is per material and not per order (ADR-012 section 3, as
        read when HU-23 was built): the most recent completed order that had that
        material, which may not be the most recent order at all. Otherwise a
        material bought two orders ago would count as never bought, and the
        same_material rule would only ever fire on consecutive orders.

        Built by hand rather than from self.select(), like ordered_by_resource
        above and for the same reason: the row this answers about is an order's,
        so the firm is pinned on purchase_order, where the tenant of the whole
        shape lives.
        """
        per_order = (
            select(
                PurchaseOrder.id.label("order_id"),
                PurchaseOrder.received_at.label("received_at"),
                PurchaseOrderLine.resource_id.label("resource_id"),
                func.sum(PurchaseOrderReceiptLine.quantity).label("quantity"),
            )
            .join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
            .join(
                PurchaseOrderReceipt,
                PurchaseOrderReceipt.purchase_order_id == PurchaseOrder.id,
            )
            .join(
                PurchaseOrderReceiptLine,
                (PurchaseOrderReceiptLine.receipt_id == PurchaseOrderReceipt.id)
                & (PurchaseOrderReceiptLine.purchase_order_line_id == PurchaseOrderLine.id),
            )
            .where(
                PurchaseOrder.firm_id == self.firm_id,
                PurchaseOrder.is_active,
                PurchaseOrder.status == "received",
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.id != besides,
                PurchaseOrderLine.is_active,
                PurchaseOrderReceipt.is_active,
            )
            .group_by(PurchaseOrder.id, PurchaseOrder.received_at, PurchaseOrderLine.resource_id)
            .subquery()
        )
        # DISTINCT ON keeps one row per material: the one from the order that
        # completed last, by received_at and then by id, as ADR-012 section 3 says.
        rows = self.db.execute(
            select(per_order.c.resource_id, per_order.c.quantity)
            .distinct(per_order.c.resource_id)
            .order_by(
                per_order.c.resource_id,
                per_order.c.received_at.desc(),
                per_order.c.order_id.desc(),
            )
        ).all()
        return {resource_id: quantity for resource_id, quantity in rows}


@dataclass(frozen=True)
class ReceiptLineEntry:
    """How much of one order line arrived in one delivery, and what it was paid."""

    purchase_order_line_id: int
    quantity: Decimal
    actual_cost: Decimal


@dataclass(frozen=True)
class ReceiptEntry:
    """One delivery of an order, with its lines and the name of whoever loaded it."""

    receipt: PurchaseOrderReceipt
    created_by_name: str
    lines: tuple[ReceiptLineEntry, ...]


@dataclass(frozen=True)
class ReceivedTotals:
    """What one order line has received in all, across the order's live receipts."""

    quantity: Decimal
    actual_cost: Decimal


class PurchaseOrderReceiptRepository(FirmScopedRepository[PurchaseOrderReceipt]):
    """This firm's live receipts. A cancelled one is simply not here (ADR-011 section 3)."""

    model = PurchaseOrderReceipt

    def get(self, order_id: int, receipt_id: int) -> PurchaseOrderReceipt | None:
        """A live receipt of this order. Never reachable through an order it is not on."""
        return self.db.scalars(
            self.select().where(
                PurchaseOrderReceipt.purchase_order_id == order_id,
                PurchaseOrderReceipt.id == receipt_id,
            )
        ).first()

    def last(self, order_id: int) -> PurchaseOrderReceipt | None:
        """The last receipt loaded on this order: the only one that may be cancelled.

        By id and not by received_on. ADR-011 section 3 allows cancelling the last
        one so that no later receipt is left standing on a base that no longer
        exists, and that base is the order of loading: a delivery entered today
        was computed over everything entered before it, whatever day it arrived.
        """
        return self.db.scalars(
            self.select()
            .where(PurchaseOrderReceipt.purchase_order_id == order_id)
            .order_by(PurchaseOrderReceipt.id.desc())
            .limit(1)
        ).first()

    def for_order(self, order_id: int) -> list[ReceiptEntry]:
        """The order's live receipts, oldest delivery first, each with its lines."""
        rows = self.db.execute(
            self.select()
            .join(Account, Account.id == PurchaseOrderReceipt.created_by)
            .add_columns(Account.name)
            .where(PurchaseOrderReceipt.purchase_order_id == order_id)
            .order_by(PurchaseOrderReceipt.received_on, PurchaseOrderReceipt.id)
        ).all()
        lines = self._lines([receipt.id for receipt, _ in rows])
        return [
            ReceiptEntry(
                receipt=receipt,
                created_by_name=author,
                lines=tuple(lines.get(receipt.id, ())),
            )
            for receipt, author in rows
        ]

    def _lines(self, receipt_ids: Collection[int]) -> dict[int, list[ReceiptLineEntry]]:
        """The lines of these receipts, by receipt.

        A plain read by receipt_id: the rows carry no firm of their own, and the
        ids come from receipts this repository already narrowed to one firm.
        """
        if not receipt_ids:
            return {}
        rows = self.db.execute(
            select(
                PurchaseOrderReceiptLine.receipt_id,
                PurchaseOrderReceiptLine.purchase_order_line_id,
                PurchaseOrderReceiptLine.quantity,
                PurchaseOrderReceiptLine.actual_cost,
            ).where(PurchaseOrderReceiptLine.receipt_id.in_(receipt_ids))
        ).all()
        by_receipt: dict[int, list[ReceiptLineEntry]] = defaultdict(list)
        for receipt_id, line_id, quantity, actual_cost in rows:
            by_receipt[receipt_id].append(
                ReceiptLineEntry(
                    purchase_order_line_id=line_id, quantity=quantity, actual_cost=actual_cost
                )
            )
        return by_receipt

    def received_by_line(self, order_id: int) -> dict[int, ReceivedTotals]:
        """Per line of this order, what its live receipts add up to.

        The one number the ceiling of ADR-011 section 7 rule 1 is measured against,
        and the one the two received statuses are derived from. Cancelled
        receipts are out by the join: self.select() already drops them.
        """
        rows = self.db.execute(
            select(
                PurchaseOrderReceiptLine.purchase_order_line_id,
                func.sum(PurchaseOrderReceiptLine.quantity),
                func.sum(PurchaseOrderReceiptLine.actual_cost),
            )
            .join(
                PurchaseOrderReceipt,
                PurchaseOrderReceipt.id == PurchaseOrderReceiptLine.receipt_id,
            )
            .where(
                PurchaseOrderReceipt.firm_id == self.firm_id,
                PurchaseOrderReceipt.is_active,
                PurchaseOrderReceipt.purchase_order_id == order_id,
            )
            .group_by(PurchaseOrderReceiptLine.purchase_order_line_id)
        ).all()
        return {
            line_id: ReceivedTotals(quantity=quantity, actual_cost=actual_cost)
            for line_id, quantity, actual_cost in rows
        }
