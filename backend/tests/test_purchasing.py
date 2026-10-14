"""The arithmetic of HU-18's comparison (ADR-010 section 4), without a database.

The two builders of services/purchasing.py read the database and are pinned
through the API in test_purchasing_api.py; what is pinned here is the formula,
the order and the ties, which are pure.
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.repositories.supplier import OfferEntry
from app.services.purchasing import offer_total, rank

UPDATED = datetime(2026, 10, 1, tzinfo=UTC)


def offer(supplier_id: int, name: str, unit_price: str, shipping: str) -> OfferEntry:
    return OfferEntry(
        resource_id=1,
        supplier_id=supplier_id,
        supplier_name=name,
        unit_price=Decimal(unit_price),
        shipping_cost=Decimal(shipping),
        price_updated_at=UPDATED,
    )


def summary(ranked) -> list[tuple[str, Decimal, bool]]:
    return [(found.supplier_name, found.total, found.cheapest) for found in ranked]


class TestOfferTotal:
    def test_price_times_quantity_plus_shipping(self):
        assert offer_total(Decimal("230.00"), Decimal("1500.00"), Decimal("10")) == Decimal(
            "3800.00"
        )

    def test_shipping_is_added_once_whatever_the_quantity(self):
        """A fixed amount per material (ADR-010 section 3), not per unit."""
        assert offer_total(Decimal("1.00"), Decimal("500.00"), Decimal("1000")) == Decimal(
            "1500.00"
        )

    def test_the_product_is_rounded_to_the_cent_half_up(self):
        """0.125 rounds up, as Postgres' round() does in the take-off."""
        assert offer_total(Decimal("0.25"), Decimal("0"), Decimal("0.5")) == Decimal("0.13")

    def test_a_fractional_quantity_of_the_take_off(self):
        assert offer_total(Decimal("8500.00"), Decimal("0.00"), Decimal("1.234")) == Decimal(
            "10489.00"
        )


class TestRank:
    def test_cheapest_first_and_only_it_marked(self):
        ranked = rank(
            [offer(1, "Sur", "225.00", "0.00"), offer(2, "Norte", "220.00", "5000.00")],
            Decimal("7200"),
        )

        assert summary(ranked) == [
            ("Norte", Decimal("1589000.00"), True),
            ("Sur", Decimal("1620000.00"), False),
        ]

    def test_the_cheapest_depends_on_the_quantity(self):
        """Few units favour cheap shipping, many favour the cheaper unit price."""
        offers = [offer(1, "Sur", "225.00", "0.00"), offer(2, "Norte", "220.00", "5000.00")]

        assert summary(rank(offers, Decimal("10")))[0] == ("Sur", Decimal("2250.00"), True)
        assert summary(rank(offers, Decimal("7200")))[0] == ("Norte", Decimal("1589000.00"), True)

    def test_a_tie_marks_every_cheapest_one(self):
        ranked = rank(
            [
                offer(1, "Sur", "225.00", "0.00"),
                offer(2, "Este", "220.00", "50.00"),
                offer(3, "Oeste", "300.00", "0.00"),
            ],
            Decimal("10"),
        )

        assert summary(ranked) == [
            ("Este", Decimal("2250.00"), True),
            ("Sur", Decimal("2250.00"), True),
            ("Oeste", Decimal("3000.00"), False),
        ]

    def test_a_tie_is_ordered_by_name_whatever_the_input_order(self):
        offers = [offer(1, "sur", "10.00", "0.00"), offer(2, "Este", "10.00", "0.00")]

        assert [found.supplier_name for found in rank(offers, Decimal("1"))] == ["Este", "sur"]
        assert [found.supplier_name for found in rank(offers[::-1], Decimal("1"))] == [
            "Este",
            "sur",
        ]

    def test_no_offers_is_no_offers(self):
        assert rank([], Decimal("5")) == ()

    def test_a_single_offer_is_the_cheapest(self):
        (only,) = rank([offer(1, "Sur", "10.00", "0.00")], Decimal("1"))

        assert only.cheapest
