"""The rules for a firm's suppliers and their price lists (HU-17, ADR-010).

Plain functions that flush and never commit, raising their own exceptions so the
route maps them to status codes in one place, the way catalog_admin.py does for
the catalogue.

firm_id is always an argument, taken by the route from the resolved membership and
never from the request body. Every lookup goes through a firm-scoped repository, so
a supplier or a price row of another firm is simply not found.

Money is untouched here: a supplier's prices feed the comparison of HU-18 and
nothing else. The take-off, the budget and its saved versions keep computing with
resource.reference_price (ADR-010 section 5).
"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Resource, Supplier, SupplierPrice
from app.repositories.supplier import SupplierPriceRepository, SupplierRepository

SUPPLIER_NAME_TAKEN = "El estudio ya tiene un proveedor activo con ese nombre"
MATERIAL_ALREADY_LISTED = "Ese proveedor ya tiene este material en su lista"
ONLY_MATERIALS = "La lista de un proveedor solo lleva materiales, no mano de obra ni equipo"
MATERIAL_NOT_AVAILABLE = "El material no existe o fue dado de baja del catálogo"

# The fields of a supplier an edit may change. Anything else in `changes` is a
# programming error and not a client's choice, so it is refused loudly.
SUPPLIER_FIELDS = frozenset({"name", "contact_name", "contact_email", "phone", "address"})
PRICE_FIELDS = frozenset({"unit_price", "shipping_cost"})


class SupplierError(Exception):
    """A rule the current state of the firm's suppliers refuses. The route answers 409."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidMaterialError(Exception):
    """The payload names a material that cannot be priced. The route answers 422.

    422 and not 409, as with HU-8's references: the body was well formed, it is
    the thing it points at that is wrong.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class SupplierNotFoundError(Exception):
    """The supplier is not this firm's, is deactivated, or does not exist. The route answers 404."""


class SupplierPriceNotFoundError(Exception):
    """No live row of that supplier's list has this id. The route answers 404."""


def get_supplier(db: Session, firm_id: int, supplier_id: int) -> Supplier:
    """This firm's live supplier with this id, for a write to act on.

    Another firm's, a deactivated one and a missing one are the same error
    (ADR-010 section 7, rule 3): a price is never loaded into a supplier that was
    given up, and no firm learns which ids exist elsewhere.
    """
    supplier = SupplierRepository(db, firm_id=firm_id).get(supplier_id)
    if supplier is None:
        raise SupplierNotFoundError
    return supplier


def create_supplier(
    db: Session,
    firm_id: int,
    *,
    name: str,
    contact_name: str | None = None,
    contact_email: str | None = None,
    phone: str | None = None,
    address: str | None = None,
) -> Supplier:
    """Add a supplier to this firm."""
    if SupplierRepository(db, firm_id=firm_id).name_taken(name):
        raise SupplierError(SUPPLIER_NAME_TAKEN)

    supplier = Supplier(
        firm_id=firm_id,
        name=name,
        contact_name=contact_name,
        contact_email=contact_email,
        phone=phone,
        address=address,
    )
    db.add(supplier)
    db.flush()
    return supplier


def update_supplier(
    db: Session, firm_id: int, supplier_id: int, changes: dict[str, Any]
) -> Supplier:
    """Apply what the architect changed, and nothing else.

    `changes` holds only the fields the request sent: an absent field is left as it
    was and a field sent as null is cleared.
    """
    unknown = set(changes) - SUPPLIER_FIELDS
    if unknown:
        raise ValueError(f"not a supplier field: {', '.join(sorted(unknown))}")

    supplier = get_supplier(db, firm_id, supplier_id)

    new_name = changes.get("name")
    if new_name is not None and SupplierRepository(db, firm_id=firm_id).name_taken(
        new_name, exclude_id=supplier.id
    ):
        raise SupplierError(SUPPLIER_NAME_TAKEN)

    for field, value in changes.items():
        setattr(supplier, field, value)
    db.flush()
    return supplier


def deactivate_supplier(db: Session, firm_id: int, supplier_id: int) -> None:
    """Take a supplier out of use. A logical removal, with its whole list.

    Its price rows are left as they are: every read of them joins the supplier and
    asks for it to be live, which is what drops the list out of HU-18's comparison
    (ADR-010 section 7, rule 4) without touching each row.
    """
    supplier = get_supplier(db, firm_id, supplier_id)
    supplier.is_active = False
    db.flush()


def _priceable_material(db: Session, resource_id: int) -> Resource:
    """The catalogue material to price, or the reason it cannot be.

    ADR-010 section 7, rules 1 and 2: a list carries materials and not labour or
    equipment, and a material the support has deactivated is no longer offered.
    """
    resource = db.get(Resource, resource_id)
    if resource is None or not resource.is_active:
        raise InvalidMaterialError(MATERIAL_NOT_AVAILABLE)
    if resource.type != "material":
        raise InvalidMaterialError(ONLY_MATERIALS)
    return resource


def add_price(
    db: Session,
    firm_id: int,
    supplier_id: int,
    *,
    resource_id: int,
    unit_price,
    shipping_cost,
) -> SupplierPrice:
    """Price one more material in a supplier's list."""
    supplier = get_supplier(db, firm_id, supplier_id)
    resource = _priceable_material(db, resource_id)

    if SupplierPriceRepository(db, firm_id=firm_id).listed_resource(supplier.id, resource.id):
        raise SupplierError(MATERIAL_ALREADY_LISTED)

    price = SupplierPrice(
        supplier_id=supplier.id,
        firm_id=firm_id,
        resource_id=resource.id,
        unit_price=unit_price,
        shipping_cost=shipping_cost,
    )
    db.add(price)
    db.flush()
    # Read back what the database assigned (price_updated_at, currency), so the
    # response is the row as stored and not the row as the ORM guessed it.
    db.refresh(price)
    return price


def update_price(
    db: Session, firm_id: int, supplier_id: int, price_id: int, changes: dict[str, Any]
) -> SupplierPrice:
    """Change a row's amounts.

    price_updated_at moves only when an amount really changes, like
    resource.price_updated_at (ADR-005 section 5): it is the "actualizado el" of the
    screen, and saving the same numbers again must not make a price look fresher.
    """
    unknown = set(changes) - PRICE_FIELDS
    if unknown:
        raise ValueError(f"not a price field: {', '.join(sorted(unknown))}")

    get_supplier(db, firm_id, supplier_id)
    price = SupplierPriceRepository(db, firm_id=firm_id).get(supplier_id, price_id)
    if price is None:
        raise SupplierPriceNotFoundError

    moved = any(getattr(price, field) != value for field, value in changes.items())
    for field, value in changes.items():
        setattr(price, field, value)
    if moved:
        # The database clock, like the column's default and the trigger beside it.
        price.price_updated_at = func.now()
    db.flush()
    db.refresh(price)
    return price


def deactivate_price(db: Session, firm_id: int, supplier_id: int, price_id: int) -> None:
    """Remove one row from a supplier's list. A logical removal: loading the same
    material again later creates a new row and keeps this one as history."""
    get_supplier(db, firm_id, supplier_id)
    price = SupplierPriceRepository(db, firm_id=firm_id).get(supplier_id, price_id)
    if price is None:
        raise SupplierPriceNotFoundError
    price.is_active = False
    db.flush()
