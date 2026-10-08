"""A firm's suppliers and their price lists over HTTP (HU-17, ADR-010 section 8).

Under /firms/{firm_id}: the rows belong to the firm, unlike the catalogue they point
at. Reading demands supplier.view and writing supplier.manage, both held by owner
and architect and by nobody else: a supplier's prices are the firm's costs, so the
client does not see this section at all (403, not an empty list).

There is nothing here that touches a work's budget. The prices in these lists feed
the comparison of HU-18 and no more (ADR-010 section 5).
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentMembership, DbSession, requires
from app.repositories.supplier import (
    PriceEntry,
    SupplierEntry,
    SupplierPriceRepository,
    SupplierRepository,
)
from app.schemas.catalog import UnitRef
from app.schemas.supplier import (
    PricedResource,
    SupplierCreate,
    SupplierDetailOut,
    SupplierOut,
    SupplierPriceCreate,
    SupplierPriceOut,
    SupplierPriceUpdate,
    SupplierUpdate,
)
from app.services import suppliers

router = APIRouter(prefix="/firms/{firm_id}/suppliers", tags=["suppliers"])

SUPPLIER_NOT_FOUND = "Proveedor no encontrado"
PRICE_NOT_FOUND = "Precio no encontrado en la lista del proveedor"

VIEW = requires("supplier.view", "firm")
MANAGE = requires("supplier.manage", "firm")


@contextmanager
def _supplier_rules() -> Iterator[None]:
    """Where a broken rule of suppliers.py becomes a status code, for every write here.

    404 when the id in the URL names nothing this firm may reach (another firm's, a
    deactivated one, a missing one), 409 for a rule the firm's current suppliers
    refuse (a repeated name, a material already in the list) and 422 for a material
    the payload names that cannot be priced.
    """
    try:
        yield
    except suppliers.SupplierNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=SUPPLIER_NOT_FOUND) from None
    except suppliers.SupplierPriceNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=PRICE_NOT_FOUND) from None
    except suppliers.InvalidMaterialError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error.detail) from None
    except suppliers.SupplierError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _supplier_out(entry: SupplierEntry) -> SupplierOut:
    supplier = entry.supplier
    return SupplierOut(
        id=supplier.id,
        name=supplier.name,
        contact_name=supplier.contact_name,
        contact_email=supplier.contact_email,
        phone=supplier.phone,
        address=supplier.address,
        price_count=entry.price_count,
    )


def _price_out(entry: PriceEntry) -> SupplierPriceOut:
    price, resource = entry.price, entry.resource
    return SupplierPriceOut(
        id=price.id,
        resource=PricedResource(
            id=resource.id,
            name=resource.name,
            unit=UnitRef(code=entry.unit_code, abbreviation=entry.unit_abbreviation),
            reference_price=resource.reference_price,
        ),
        unit_price=price.unit_price,
        shipping_cost=price.shipping_cost,
        currency=price.currency,
        price_updated_at=price.price_updated_at,
    )


def _list_out(db: DbSession, membership: CurrentMembership, supplier_id: int) -> SupplierDetailOut:
    """A supplier with its whole list, read back as the screen will show it."""
    firm_id = membership.firm_id
    supplier = suppliers.get_supplier(db, firm_id, supplier_id)
    entries = SupplierPriceRepository(db, firm_id=firm_id).entries(supplier.id)
    prices = [_price_out(entry) for entry in entries]
    base = _supplier_out(SupplierEntry(supplier=supplier, price_count=len(prices)))
    return SupplierDetailOut(**base.model_dump(), prices=prices)


@router.get("", response_model=list[SupplierOut], dependencies=[Depends(VIEW)])
def list_suppliers(db: DbSession, membership: CurrentMembership) -> list[SupplierOut]:
    """Every live supplier of this firm, by name. The firm comes from the resolved
    membership and never from the raw path, like every other firm route."""
    entries = SupplierRepository(db, firm_id=membership.firm_id).entries()
    return [_supplier_out(entry) for entry in entries]


@router.post(
    "",
    response_model=SupplierOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def create_supplier(
    payload: SupplierCreate, db: DbSession, membership: CurrentMembership
) -> SupplierOut:
    """Add a supplier. firm_id comes from the membership, never the body."""
    with _supplier_rules():
        supplier = suppliers.create_supplier(db, membership.firm_id, **payload.model_dump())
    db.commit()
    return _supplier_out(SupplierEntry(supplier=supplier, price_count=0))


@router.get("/{supplier_id}", response_model=SupplierDetailOut, dependencies=[Depends(VIEW)])
def read_supplier(
    supplier_id: int, db: DbSession, membership: CurrentMembership
) -> SupplierDetailOut:
    """One supplier with its price list."""
    with _supplier_rules():
        return _list_out(db, membership, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierOut, dependencies=[Depends(MANAGE)])
def update_supplier(
    supplier_id: int, payload: SupplierUpdate, db: DbSession, membership: CurrentMembership
) -> SupplierOut:
    """Change what was sent. A field sent as null is cleared; one not sent is kept."""
    with _supplier_rules():
        supplier = suppliers.update_supplier(
            db,
            membership.firm_id,
            supplier_id,
            payload.model_dump(exclude_unset=True),
        )
    db.commit()
    count = len(SupplierPriceRepository(db, firm_id=membership.firm_id).entries(supplier.id))
    return _supplier_out(SupplierEntry(supplier=supplier, price_count=count))


@router.post(
    "/{supplier_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def deactivate_supplier(supplier_id: int, db: DbSession, membership: CurrentMembership) -> None:
    """Give a supplier up, with its whole list. 204: the frontend already has the row.

    A POST and not a DELETE: nothing is deleted, the row is kept (baja lógica).
    """
    with _supplier_rules():
        suppliers.deactivate_supplier(db, membership.firm_id, supplier_id)
    db.commit()


@router.get(
    "/{supplier_id}/prices",
    response_model=list[SupplierPriceOut],
    dependencies=[Depends(VIEW)],
)
def list_prices(
    supplier_id: int, db: DbSession, membership: CurrentMembership
) -> list[SupplierPriceOut]:
    """One supplier's list, by material."""
    with _supplier_rules():
        supplier = suppliers.get_supplier(db, membership.firm_id, supplier_id)
    entries = SupplierPriceRepository(db, firm_id=membership.firm_id).entries(supplier.id)
    return [_price_out(entry) for entry in entries]


@router.post(
    "/{supplier_id}/prices",
    response_model=SupplierPriceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE)],
)
def add_price(
    supplier_id: int,
    payload: SupplierPriceCreate,
    db: DbSession,
    membership: CurrentMembership,
) -> SupplierPriceOut:
    """Price one more material in this supplier's list."""
    with _supplier_rules():
        price = suppliers.add_price(
            db,
            membership.firm_id,
            supplier_id,
            resource_id=payload.resource_id,
            unit_price=payload.unit_price,
            shipping_cost=payload.shipping_cost,
        )
    db.commit()
    return _price_row(db, membership, supplier_id, price.id)


@router.patch(
    "/{supplier_id}/prices/{price_id}",
    response_model=SupplierPriceOut,
    dependencies=[Depends(MANAGE)],
)
def update_price(
    supplier_id: int,
    price_id: int,
    payload: SupplierPriceUpdate,
    db: DbSession,
    membership: CurrentMembership,
) -> SupplierPriceOut:
    """Change a row's amounts. The material is not editable."""
    with _supplier_rules():
        price = suppliers.update_price(
            db,
            membership.firm_id,
            supplier_id,
            price_id,
            payload.model_dump(exclude_unset=True),
        )
    db.commit()
    return _price_row(db, membership, supplier_id, price.id)


@router.post(
    "/{supplier_id}/prices/{price_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE)],
)
def deactivate_price(
    supplier_id: int, price_id: int, db: DbSession, membership: CurrentMembership
) -> None:
    """Remove a row from the list. 204: the frontend already has the row."""
    with _supplier_rules():
        suppliers.deactivate_price(db, membership.firm_id, supplier_id, price_id)
    db.commit()


def _price_row(
    db: DbSession, membership: CurrentMembership, supplier_id: int, price_id: int
) -> SupplierPriceOut:
    """The row a write just produced, in the shape the list uses."""
    entry = SupplierPriceRepository(db, firm_id=membership.firm_id).entry(supplier_id, price_id)
    return _price_out(entry)
