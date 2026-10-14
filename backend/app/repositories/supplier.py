"""Reaching a firm's suppliers and their price lists, and only those (HU-17, ADR-010).

Both repositories start from FirmScopedRepository.select(), so a read already
carries firm_id = :firm and is_active before any subclass narrows it further. A
supplier of another firm, a deactivated one and one that never existed are the
same None here, and the route answers all three with the same 404.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Resource, Supplier, SupplierPrice, UnitOfMeasure
from app.repositories.base import FirmScopedRepository


@dataclass(frozen=True)
class SupplierEntry:
    """One row of the suppliers listing: the supplier and how long its list is."""

    supplier: Supplier
    price_count: int


@dataclass(frozen=True)
class PriceEntry:
    """One row of a price list, with the material it prices already looked up.

    The material's own reference price travels along because the screen has to say
    which of the two prices it is showing (ADR-010 section 5): the supplier's, and
    the one the budget keeps computing with.
    """

    price: SupplierPrice
    resource: Resource
    unit_code: str
    unit_abbreviation: str


@dataclass(frozen=True)
class OfferEntry:
    """What one supplier asks for one material: a row of HU-18's comparison."""

    resource_id: int
    supplier_id: int
    supplier_name: str
    unit_price: Decimal
    shipping_cost: Decimal
    price_updated_at: datetime


class SupplierRepository(FirmScopedRepository[Supplier]):
    """This firm's live suppliers."""

    model = Supplier

    def get(self, supplier_id: int) -> Supplier | None:
        """The supplier, or None.

        None covers "does not exist", "belongs to another firm" and "was
        deactivated" alike, so a firm never learns which ids exist elsewhere.
        """
        return self.db.scalars(self.select().where(Supplier.id == supplier_id)).first()

    def entries(self) -> list[SupplierEntry]:
        """Every live supplier, by name, with the length of its live price list."""
        price_count = (
            select(func.count())
            .where(SupplierPrice.supplier_id == Supplier.id, SupplierPrice.is_active)
            .correlate(Supplier)
            .scalar_subquery()
        )
        rows = self.db.execute(
            self.select().add_columns(price_count).order_by(func.lower(Supplier.name), Supplier.id)
        ).all()
        return [SupplierEntry(supplier=supplier, price_count=count) for supplier, count in rows]

    def name_taken(self, name: str, *, exclude_id: int | None = None) -> bool:
        """Whether another live supplier of this firm answers to this name.

        Case-insensitive, mirroring uq_supplier_name_active: "Corralón Norte" and
        "corralón norte" are the same name. exclude_id leaves the row itself out,
        so editing a supplier without renaming it does not collide with itself.
        """
        statement = self.select().where(func.lower(Supplier.name) == name.lower())
        if exclude_id is not None:
            statement = statement.where(Supplier.id != exclude_id)
        return self.db.scalars(statement.limit(1)).first() is not None

    def any(self) -> bool:
        """Whether this firm has a live supplier at all: HU-18's empty state."""
        return self.db.scalars(self.select().limit(1)).first() is not None


class SupplierPriceRepository(FirmScopedRepository[SupplierPrice]):
    """This firm's live price rows, of live suppliers."""

    model = SupplierPrice

    def _entries(self):
        """The base select with the material and its unit joined in.

        The supplier is joined to be filtered on: a live row of a deactivated
        supplier is out of every read, with its whole list (ADR-010 section 7,
        rule 4).
        """
        return (
            self.select()
            .join(Supplier, Supplier.id == SupplierPrice.supplier_id)
            .where(Supplier.is_active)
            .join(Resource, Resource.id == SupplierPrice.resource_id)
            .join(UnitOfMeasure, UnitOfMeasure.id == Resource.unit_of_measure_id)
            .add_columns(Resource, UnitOfMeasure.code, UnitOfMeasure.abbreviation)
        )

    def entries(self, supplier_id: int) -> list[PriceEntry]:
        """One supplier's list, by material name."""
        rows = self.db.execute(
            self._entries()
            .where(SupplierPrice.supplier_id == supplier_id)
            .order_by(func.lower(Resource.name), SupplierPrice.id)
        ).all()
        return [PriceEntry(*row) for row in rows]

    def entry(self, supplier_id: int, price_id: int) -> PriceEntry | None:
        """One row of this supplier's list, or None.

        Looked up by both ids: a price row is never reachable through a supplier
        it does not belong to.
        """
        row = self.db.execute(
            self._entries().where(
                SupplierPrice.supplier_id == supplier_id, SupplierPrice.id == price_id
            )
        ).first()
        return PriceEntry(*row) if row is not None else None

    def get(self, supplier_id: int, price_id: int) -> SupplierPrice | None:
        entry = self.entry(supplier_id, price_id)
        return entry.price if entry is not None else None

    def listed_resource(self, supplier_id: int, resource_id: int) -> SupplierPrice | None:
        """The live row that already prices this material for this supplier, if any."""
        return self.db.scalars(
            self.select().where(
                SupplierPrice.supplier_id == supplier_id, SupplierPrice.resource_id == resource_id
            )
        ).first()

    def offers(self, resource_ids: Collection[int]) -> list[OfferEntry]:
        """Every live offer of these materials, across the firm's live suppliers.

        One query for a whole work's materials, not one per material. A row only
        counts while its supplier is live and the catalogue still has the
        material (ADR-010 section 7, rules 2 and 4): a material the support
        deactivated stays in the lists but is no longer offered.

        Unordered: the order depends on the quantity, so it is the comparison's
        to decide (services/purchasing.py).
        """
        if not resource_ids:
            return []
        rows = self.db.execute(
            self.select()
            .join(Supplier, Supplier.id == SupplierPrice.supplier_id)
            .where(Supplier.is_active)
            .join(Resource, Resource.id == SupplierPrice.resource_id)
            .where(Resource.is_active, SupplierPrice.resource_id.in_(resource_ids))
            .add_columns(Supplier.name)
        ).all()
        return [
            OfferEntry(
                resource_id=price.resource_id,
                supplier_id=price.supplier_id,
                supplier_name=name,
                unit_price=price.unit_price,
                shipping_cost=price.shipping_cost,
                price_updated_at=price.price_updated_at,
            )
            for price, name in rows
        ]
