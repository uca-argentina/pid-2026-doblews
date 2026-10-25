"""Purchase orders over HTTP (HU-20, ADR-011 section 8).

Two prefixes, for two reasons. Under the work live the two things that are born
there: generating drafts from its comparison, and listing its orders. Those
resolve the work like every other work route, so they serve whoever may see it.
Everything else lives under the firm: the permissions are firm-scope (ADR-011
section 6), and that is what lets an architect who is not on the work's team
manage its orders too.

Reading demands purchase_order.view and writing purchase_order.manage, both held
by owner and architect. The client holds neither: an order is the firm's costs.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    PROJECT_NOT_FOUND,
    CurrentAccount,
    CurrentMembership,
    DbSession,
    FirmPermissions,
    requires,
)
from app.repositories.project import ProjectRepository
from app.repositories.purchase_order import (
    OrderEntry,
    OrderLineEntry,
    PurchaseOrderLineRepository,
    PurchaseOrderRepository,
)
from app.schemas.catalog import UnitRef
from app.schemas.purchase_order import (
    GenerateOrdersIn,
    GenerateOrdersOut,
    NamedRef,
    OrderEvent,
    OrderLineCreate,
    OrderLineSupplierChange,
    OrderLineUpdate,
    OrderStatus,
    PurchaseOrderLineOut,
    PurchaseOrderOut,
    PurchaseOrderSummary,
    SkippedMaterialOut,
)
from app.services import purchase_orders
from app.services.purchasing import CURRENCY

router = APIRouter(tags=["purchase-orders"])

ORDER_NOT_FOUND = "Orden de compra no encontrada"
LINE_NOT_FOUND = "Renglón no encontrado en la orden"

VIEW = requires("purchase_order.view", "firm")
MANAGE = requires("purchase_order.manage", "firm")

PROJECT_PREFIX = "/firms/{firm_id}/projects/{project_id}/purchase-orders"
FIRM_PREFIX = "/firms/{firm_id}/purchase-orders"


@contextmanager
def _order_rules() -> Iterator[None]:
    """Where a broken rule of purchase_orders.py becomes a status code."""
    try:
        yield
    except purchase_orders.PurchaseOrderNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ORDER_NOT_FOUND) from None
    except purchase_orders.PurchaseOrderLineNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=LINE_NOT_FOUND) from None
    except purchase_orders.InvalidPurchaseLineError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.detail) from None
    except (purchase_orders.PurchaseOrderStateError, purchase_orders.PurchaseOrderError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _line_out(entry: OrderLineEntry) -> PurchaseOrderLineOut:
    line = entry.line
    return PurchaseOrderLineOut(
        id=line.id,
        resource=NamedRef(id=line.resource_id, name=entry.resource_name),
        unit=UnitRef(code=entry.unit_code, abbreviation=entry.unit_abbreviation),
        quantity=line.quantity,
        unit_price=line.unit_price,
        shipping_cost=line.shipping_cost,
        estimated_total=purchase_orders.line_total(line),
    )


def _summary(entry: OrderEntry, lines: list[OrderLineEntry]) -> PurchaseOrderSummary:
    order = entry.order
    return PurchaseOrderSummary(
        id=order.id,
        number=order.number,
        status=order.status,
        project=NamedRef(id=order.project_id, name=entry.project_name),
        supplier=NamedRef(id=order.supplier_id, name=entry.supplier_name),
        line_count=len(lines),
        estimated_total=purchase_orders.order_total(line.line for line in lines),
        currency=CURRENCY,
        created_at=order.created_at,
    )


def _summaries(
    db: DbSession, firm_id: int, entries: list[OrderEntry]
) -> list[PurchaseOrderSummary]:
    lines = PurchaseOrderLineRepository(db, firm_id=firm_id).lines(
        [entry.order.id for entry in entries]
    )
    return [_summary(entry, lines.get(entry.order.id, [])) for entry in entries]


def _history(db: DbSession, firm_id: int, order) -> list[OrderEvent]:
    """The order's changes of status, oldest first, from its own columns."""
    stamps = [
        ("created", order.created_at, order.created_by),
        ("issued", order.issued_at, order.issued_by),
        ("cancelled", order.cancelled_at, order.cancelled_by),
    ]
    stamps = [stamp for stamp in stamps if stamp[1] is not None]
    names = PurchaseOrderRepository(db, firm_id=firm_id).account_names(
        {account_id for _, _, account_id in stamps}
    )
    return [
        OrderEvent(kind=kind, at=at, by=NamedRef(id=account_id, name=names.get(account_id, "")))
        for kind, at, account_id in sorted(stamps, key=lambda stamp: stamp[1])
    ]


def _order_out(db: DbSession, firm_id: int, order_id: int) -> PurchaseOrderOut:
    """An order with its lines and history, read back as the screen will show it."""
    entry = PurchaseOrderRepository(db, firm_id=firm_id).entry(order_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ORDER_NOT_FOUND)
    lines = PurchaseOrderLineRepository(db, firm_id=firm_id).lines([order_id]).get(order_id, [])
    return PurchaseOrderOut(
        **_summary(entry, lines).model_dump(),
        lines=[_line_out(line) for line in lines],
        history=_history(db, firm_id, entry.order),
    )


def _visible_project(
    db: DbSession, membership: CurrentMembership, account: CurrentAccount, granted, project_id: int
):
    project = ProjectRepository(db, firm_id=membership.firm_id).get_visible(
        project_id, account.id, granted
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)
    return project


# --- under the work -----------------------------------------------------------


@router.post(
    f"{PROJECT_PREFIX}/generate",
    response_model=GenerateOrdersOut,
    dependencies=[Depends(MANAGE)],
)
def generate_orders(
    project_id: int,
    payload: GenerateOrdersIn,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
) -> GenerateOrdersOut:
    """Drafts for these materials of the work, one per supplier (ADR-011 section 5).

    200 and not 201: it may create drafts, complete existing ones, or do neither
    when every material was skipped, and the body says which.
    """
    project = _visible_project(db, membership, account, granted, project_id)
    with _order_rules():
        result = purchase_orders.generate(
            db,
            membership.firm_id,
            project.id,
            [(item.resource_id, item.supplier_id) for item in payload.items],
            account.id,
        )
    db.commit()
    entries = PurchaseOrderRepository(db, firm_id=membership.firm_id).entries(result.order_ids)
    return GenerateOrdersOut(
        orders=_summaries(db, membership.firm_id, entries),
        skipped=[
            SkippedMaterialOut(resource_id=item.resource_id, name=item.name, reason=item.reason)
            for item in result.skipped
        ],
    )


@router.get(
    PROJECT_PREFIX,
    response_model=list[PurchaseOrderSummary],
    dependencies=[Depends(VIEW)],
)
def list_project_orders(
    project_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    granted: FirmPermissions,
    db: DbSession,
    order_status: OrderStatus | None = None,
) -> list[PurchaseOrderSummary]:
    """The work's orders, newest first, optionally of one status (?order_status=draft)."""
    project = _visible_project(db, membership, account, granted, project_id)
    entries = PurchaseOrderRepository(db, firm_id=membership.firm_id).for_project(
        project.id, order_status
    )
    return _summaries(db, membership.firm_id, entries)


# --- under the firm -----------------------------------------------------------


@router.get(
    FIRM_PREFIX,
    response_model=list[PurchaseOrderSummary],
    dependencies=[Depends(VIEW)],
)
def list_firm_orders(
    db: DbSession,
    membership: CurrentMembership,
    project_id: int | None = None,
    supplier_id: int | None = None,
    order_status: OrderStatus | None = None,
) -> list[PurchaseOrderSummary]:
    """Every order of the firm, newest first, filterable by work, supplier and status.

    Not narrowed to the works the caller is on: the permission is firm-scope, and
    this listing is how an architect off a work's team reaches its orders.
    """
    entries = PurchaseOrderRepository(db, firm_id=membership.firm_id).for_firm(
        project_id, supplier_id, order_status
    )
    return _summaries(db, membership.firm_id, entries)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/issue",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def issue_order(
    order_id: int, account: CurrentAccount, db: DbSession, membership: CurrentMembership
) -> PurchaseOrderOut:
    """Issue a draft. From here on it is not edited, only received or cancelled."""
    with _order_rules():
        purchase_orders.issue(db, membership.firm_id, order_id, account.id)
    db.commit()
    return _order_out(db, membership.firm_id, order_id)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/cancel",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def cancel_order(
    order_id: int, account: CurrentAccount, db: DbSession, membership: CurrentMembership
) -> PurchaseOrderOut:
    """Cancel a draft or an issued order. Final, and it stays visible with its status."""
    with _order_rules():
        purchase_orders.cancel(db, membership.firm_id, order_id, account.id)
    db.commit()
    return _order_out(db, membership.firm_id, order_id)


@router.get(
    f"{FIRM_PREFIX}/{{order_id}}",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(VIEW)],
)
def read_order(order_id: int, db: DbSession, membership: CurrentMembership) -> PurchaseOrderOut:
    """One order with its lines. Another firm's and a discarded draft are the same 404."""
    return _order_out(db, membership.firm_id, order_id)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/lines",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def add_line(
    order_id: int, payload: OrderLineCreate, db: DbSession, membership: CurrentMembership
) -> PurchaseOrderOut:
    """Add a material of the work's take-off to a draft, at its supplier's price today."""
    with _order_rules():
        purchase_orders.add_line(
            db, membership.firm_id, order_id, payload.resource_id, payload.quantity
        )
    db.commit()
    return _order_out(db, membership.firm_id, order_id)


@router.patch(
    f"{FIRM_PREFIX}/{{order_id}}/lines/{{line_id}}",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def update_line(
    order_id: int,
    line_id: int,
    payload: OrderLineUpdate,
    db: DbSession,
    membership: CurrentMembership,
) -> PurchaseOrderOut:
    """Change how much a draft's line asks for. Its price stays the one it froze."""
    with _order_rules():
        purchase_orders.update_line(db, membership.firm_id, order_id, line_id, payload.quantity)
    db.commit()
    return _order_out(db, membership.firm_id, order_id)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/lines/{{line_id}}/supplier",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def change_line_supplier(
    order_id: int,
    line_id: int,
    payload: OrderLineSupplierChange,
    account: CurrentAccount,
    db: DbSession,
    membership: CurrentMembership,
) -> PurchaseOrderOut:
    """Move a line to another supplier's draft. Answers with the draft it landed in."""
    with _order_rules():
        target = purchase_orders.change_line_supplier(
            db, membership.firm_id, order_id, line_id, payload.supplier_id, account.id
        )
    db.commit()
    return _order_out(db, membership.firm_id, target.id)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/lines/{{line_id}}/deactivate",
    response_model=PurchaseOrderOut,
    dependencies=[Depends(MANAGE)],
)
def deactivate_line(
    order_id: int, line_id: int, db: DbSession, membership: CurrentMembership
) -> PurchaseOrderOut:
    """Take a line out of a draft. A POST and not a DELETE: nothing is erased."""
    with _order_rules():
        purchase_orders.deactivate_line(db, membership.firm_id, order_id, line_id)
    db.commit()
    return _order_out(db, membership.firm_id, order_id)


@router.post(
    f"{FIRM_PREFIX}/{{order_id}}/discard",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def discard_order(order_id: int, db: DbSession, membership: CurrentMembership) -> None:
    """Discard a draft. 204: it is gone from every listing, there is nothing to show."""
    with _order_rules():
        purchase_orders.discard(db, membership.firm_id, order_id)
    db.commit()
