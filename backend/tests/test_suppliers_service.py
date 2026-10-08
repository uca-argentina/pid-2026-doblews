"""The rules for a firm's suppliers and their price lists (HU-17, ADR-010), on the service.

The status codes are test_suppliers_api.py's business; here it is what gets written,
and what a firm can and cannot reach. Firm A is the one writing; firm B is the one it
must never touch.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models import Resource, Supplier, SupplierPrice
from app.repositories.supplier import SupplierPriceRepository, SupplierRepository
from app.services.suppliers import (
    MATERIAL_ALREADY_LISTED,
    MATERIAL_NOT_AVAILABLE,
    ONLY_MATERIALS,
    SUPPLIER_NAME_TAKEN,
    InvalidMaterialError,
    SupplierError,
    SupplierNotFoundError,
    SupplierPriceNotFoundError,
    add_price,
    create_supplier,
    deactivate_price,
    deactivate_supplier,
    update_price,
    update_supplier,
)

BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"
LABOR = "Oficial"


def supplier(db_session, firm_id, name="Corralón Norte", **overrides) -> Supplier:
    return create_supplier(db_session, firm_id, name=name, **overrides)


def price(db_session, firm_id, supplier_id, resource_id, material=BRICK, **overrides):
    """Price one seeded material, unless told otherwise."""
    fields = {
        "resource_id": resource_id[material],
        "unit_price": Decimal("230.00"),
        "shipping_cost": Decimal("1500.00"),
    } | overrides
    return add_price(db_session, firm_id, supplier_id, **fields)


class TestCreateSupplier:
    def test_the_supplier_belongs_to_the_firm_it_was_written_for(self, db_session, world):
        created = supplier(db_session, world.firm_a, contact_name="Marta", phone="388 555 0101")

        assert (created.firm_id, created.is_active) == (world.firm_a, True)
        assert (created.contact_name, created.phone) == ("Marta", "388 555 0101")

    def test_refuses_a_name_the_firm_already_uses_in_any_capitalisation(self, db_session, world):
        supplier(db_session, world.firm_a)

        with pytest.raises(SupplierError) as refused:
            supplier(db_session, world.firm_a, name="CORRALÓN NORTE")

        assert refused.value.detail == SUPPLIER_NAME_TAKEN

    def test_two_firms_may_each_have_a_supplier_of_the_same_name(self, db_session, world):
        supplier(db_session, world.firm_a)

        assert supplier(db_session, world.firm_b).firm_id == world.firm_b

    def test_a_deactivated_supplier_frees_its_name(self, db_session, world):
        first = supplier(db_session, world.firm_a)
        deactivate_supplier(db_session, world.firm_a, first.id)

        assert supplier(db_session, world.firm_a).id != first.id


class TestUpdateSupplier:
    def test_changes_only_what_was_sent(self, db_session, world):
        created = supplier(
            db_session, world.firm_a, contact_name="Marta", contact_email="marta@norte.com"
        )

        update_supplier(db_session, world.firm_a, created.id, {"phone": "388 555 0101"})

        assert (created.contact_name, created.contact_email, created.phone) == (
            "Marta",
            "marta@norte.com",
            "388 555 0101",
        )

    def test_a_field_sent_as_none_is_cleared(self, db_session, world):
        created = supplier(db_session, world.firm_a, contact_email="marta@norte.com")

        update_supplier(db_session, world.firm_a, created.id, {"contact_email": None})

        assert created.contact_email is None

    def test_keeping_its_own_name_does_not_collide_with_itself(self, db_session, world):
        created = supplier(db_session, world.firm_a)

        update_supplier(db_session, world.firm_a, created.id, {"name": "corralón norte"})

        assert created.name == "corralón norte"

    def test_refuses_a_name_another_supplier_of_the_firm_uses(self, db_session, world):
        supplier(db_session, world.firm_a, name="Corralón Sur")
        other = supplier(db_session, world.firm_a)

        with pytest.raises(SupplierError) as refused:
            update_supplier(db_session, world.firm_a, other.id, {"name": "Corralón Sur"})

        assert refused.value.detail == SUPPLIER_NAME_TAKEN

    def test_refuses_a_field_that_is_not_the_supplier_s(self, db_session, world):
        """firm_id in particular: a supplier never moves between firms."""
        created = supplier(db_session, world.firm_a)

        with pytest.raises(ValueError, match="firm_id"):
            update_supplier(db_session, world.firm_a, created.id, {"firm_id": world.firm_b})


class TestReachingASupplier:
    def test_another_firm_s_supplier_is_not_found(self, db_session, world):
        theirs = supplier(db_session, world.firm_b)

        with pytest.raises(SupplierNotFoundError):
            update_supplier(db_session, world.firm_a, theirs.id, {"phone": "1"})
        with pytest.raises(SupplierNotFoundError):
            deactivate_supplier(db_session, world.firm_a, theirs.id)

        assert theirs.is_active is True

    def test_a_deactivated_supplier_is_not_found(self, db_session, world):
        created = supplier(db_session, world.firm_a)
        deactivate_supplier(db_session, world.firm_a, created.id)

        with pytest.raises(SupplierNotFoundError):
            update_supplier(db_session, world.firm_a, created.id, {"phone": "1"})

    def test_a_missing_supplier_is_not_found(self, db_session, world):
        with pytest.raises(SupplierNotFoundError):
            deactivate_supplier(db_session, world.firm_a, 999_999)

    def test_the_listing_has_this_firm_s_live_suppliers_by_name(self, db_session, world):
        supplier(db_session, world.firm_a, name="Zeta")
        gone = supplier(db_session, world.firm_a, name="Beta")
        supplier(db_session, world.firm_a, name="alfa")
        supplier(db_session, world.firm_b, name="De otro estudio")
        deactivate_supplier(db_session, world.firm_a, gone.id)

        names = [e.supplier.name for e in SupplierRepository(db_session, world.firm_a).entries()]

        assert names == ["alfa", "Zeta"]


class TestAddPrice:
    def test_stores_the_amounts_and_stamps_the_date(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)

        row = price(db_session, world.firm_a, created.id, resource_id)

        assert (row.unit_price, row.shipping_cost, row.currency) == (
            Decimal("230.00"),
            Decimal("1500.00"),
            "ARS",
        )
        assert (row.firm_id, row.supplier_id) == (world.firm_a, created.id)
        assert row.price_updated_at is not None

    def test_shipping_may_be_zero(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)

        row = price(db_session, world.firm_a, created.id, resource_id, shipping_cost=Decimal(0))

        assert row.shipping_cost == Decimal("0.00")

    def test_refuses_labour_and_equipment(self, db_session, world, resource_id):
        """ADR-010 section 7, rule 1: a list carries materials."""
        created = supplier(db_session, world.firm_a)

        with pytest.raises(InvalidMaterialError) as refused:
            price(db_session, world.firm_a, created.id, resource_id, material=LABOR)

        assert refused.value.detail == ONLY_MATERIALS

    def test_refuses_a_material_the_support_deactivated(self, db_session, world, resource_id):
        """Rule 2: only an active material of the catalogue is offered."""
        created = supplier(db_session, world.firm_a)
        db_session.get(Resource, resource_id[BRICK]).is_active = False
        db_session.flush()

        with pytest.raises(InvalidMaterialError) as refused:
            price(db_session, world.firm_a, created.id, resource_id)

        assert refused.value.detail == MATERIAL_NOT_AVAILABLE

    def test_refuses_a_material_that_does_not_exist(self, db_session, world):
        created = supplier(db_session, world.firm_a)

        with pytest.raises(InvalidMaterialError) as refused:
            add_price(
                db_session,
                world.firm_a,
                created.id,
                resource_id=999_999,
                unit_price=Decimal(1),
                shipping_cost=Decimal(0),
            )

        assert refused.value.detail == MATERIAL_NOT_AVAILABLE

    def test_a_supplier_does_not_repeat_a_material(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)
        price(db_session, world.firm_a, created.id, resource_id)

        with pytest.raises(SupplierError) as refused:
            price(db_session, world.firm_a, created.id, resource_id, unit_price=Decimal(1))

        assert refused.value.detail == MATERIAL_ALREADY_LISTED

    def test_a_material_may_be_in_the_lists_of_several_suppliers(
        self, db_session, world, resource_id
    ):
        first = supplier(db_session, world.firm_a, name="Corralón uno")
        second = supplier(db_session, world.firm_a, name="Corralón dos")

        price(db_session, world.firm_a, first.id, resource_id, unit_price=Decimal("230.00"))
        price(db_session, world.firm_a, second.id, resource_id, unit_price=Decimal("215.00"))

        rows = db_session.query(SupplierPrice).filter_by(resource_id=resource_id[BRICK]).all()
        assert sorted(row.unit_price for row in rows) == [Decimal("215.00"), Decimal("230.00")]

    def test_nothing_is_loaded_into_a_deactivated_supplier(self, db_session, world, resource_id):
        """Rule 3."""
        created = supplier(db_session, world.firm_a)
        deactivate_supplier(db_session, world.firm_a, created.id)

        with pytest.raises(SupplierNotFoundError):
            price(db_session, world.firm_a, created.id, resource_id)

    def test_nothing_is_loaded_into_another_firm_s_supplier(self, db_session, world, resource_id):
        theirs = supplier(db_session, world.firm_b)

        with pytest.raises(SupplierNotFoundError):
            price(db_session, world.firm_a, theirs.id, resource_id)

        assert db_session.query(SupplierPrice).count() == 0

    def test_a_removed_row_can_be_loaded_again(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)
        first = price(db_session, world.firm_a, created.id, resource_id)
        deactivate_price(db_session, world.firm_a, created.id, first.id)

        again = price(db_session, world.firm_a, created.id, resource_id, unit_price=Decimal(300))

        assert again.id != first.id
        assert first.is_active is False


class TestUpdatePrice:
    def test_changing_an_amount_moves_the_date(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)
        row = price(db_session, world.firm_a, created.id, resource_id)
        row.price_updated_at = datetime(2000, 1, 1, tzinfo=UTC)
        db_session.flush()

        update_price(
            db_session, world.firm_a, created.id, row.id, {"unit_price": Decimal("260.00")}
        )

        assert row.unit_price == Decimal("260.00")
        assert row.price_updated_at.year != 2000

    def test_saving_the_same_amounts_does_not_make_the_price_look_fresher(
        self, db_session, world, resource_id
    ):
        created = supplier(db_session, world.firm_a)
        row = price(db_session, world.firm_a, created.id, resource_id)
        row.price_updated_at = datetime(2000, 1, 1, tzinfo=UTC)
        db_session.flush()

        update_price(
            db_session,
            world.firm_a,
            created.id,
            row.id,
            {"unit_price": Decimal("230.00"), "shipping_cost": Decimal("1500.00")},
        )

        assert row.price_updated_at.year == 2000

    def test_refuses_a_field_that_is_not_an_amount(self, db_session, world, resource_id):
        """The material of a row is not editable, nor is its firm."""
        created = supplier(db_session, world.firm_a)
        row = price(db_session, world.firm_a, created.id, resource_id)

        with pytest.raises(ValueError, match="resource_id"):
            update_price(db_session, world.firm_a, created.id, row.id, {"resource_id": 1})

    def test_a_row_is_not_reachable_through_another_suppliers_id(
        self, db_session, world, resource_id
    ):
        mine = supplier(db_session, world.firm_a, name="Uno")
        other = supplier(db_session, world.firm_a, name="Dos")
        row = price(db_session, world.firm_a, mine.id, resource_id)

        with pytest.raises(SupplierPriceNotFoundError):
            update_price(db_session, world.firm_a, other.id, row.id, {"unit_price": Decimal(1)})
        with pytest.raises(SupplierPriceNotFoundError):
            deactivate_price(db_session, world.firm_a, other.id, row.id)

    def test_another_firm_s_row_is_not_found(self, db_session, world, resource_id):
        theirs = supplier(db_session, world.firm_b)
        row = price(db_session, world.firm_b, theirs.id, resource_id)

        with pytest.raises(SupplierNotFoundError):
            update_price(db_session, world.firm_a, theirs.id, row.id, {"unit_price": Decimal(1)})

        assert row.unit_price == Decimal("230.00")


class TestReadingPrices:
    def test_a_deactivated_supplier_takes_its_whole_list_out_of_every_read(
        self, db_session, world, resource_id
    ):
        """Rule 4, and what HU-18's comparison relies on: the rows stay active, the
        supplier is what is asked to be live."""
        created = supplier(db_session, world.firm_a)
        row = price(db_session, world.firm_a, created.id, resource_id)
        deactivate_supplier(db_session, world.firm_a, created.id)

        repository = SupplierPriceRepository(db_session, world.firm_a)

        assert row.is_active is True
        assert repository.entries(created.id) == []
        assert repository.entry(created.id, row.id) is None

    def test_the_list_is_by_material_name_with_its_unit_and_reference_price(
        self, db_session, world, resource_id
    ):
        created = supplier(db_session, world.firm_a)
        price(db_session, world.firm_a, created.id, resource_id, material=CEMENT)
        price(db_session, world.firm_a, created.id, resource_id, material=BRICK)

        entries = SupplierPriceRepository(db_session, world.firm_a).entries(created.id)

        assert [entry.resource.name for entry in entries] == [BRICK, CEMENT]
        assert all(entry.unit_abbreviation for entry in entries)
        assert all(entry.resource.reference_price > 0 for entry in entries)

    def test_another_firm_reads_nothing_of_this_list(self, db_session, world, resource_id):
        created = supplier(db_session, world.firm_a)
        price(db_session, world.firm_a, created.id, resource_id)

        assert SupplierPriceRepository(db_session, world.firm_b).entries(created.id) == []
