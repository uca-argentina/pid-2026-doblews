"""The points rule of HU-23 and the levels of HU-24, without a database.

services/loyalty.rate() is pure, like projection.py and purchasing.py beside it:
it takes the lines of an order and what came last time, and answers with a code
and a number per line.

The orders here are always to the same supplier. 1,000 bricks last time, so
"similar" runs from 500 to 1,500 inclusive — the border counts as inside.
"""

from decimal import Decimal

import pytest

from app.services.loyalty import (
    FIRST_PURCHASE,
    LEVELS,
    POINTS,
    SAME_MATERIAL,
    SAME_MATERIAL_SIMILAR_QUANTITY,
    SAME_SUPPLIER,
    EarnedPoints,
    PurchasedLine,
    is_similar,
    level_for,
    rate,
)

BRICK = 10
CEMENT = 20
SAND = 30

LAST_TIME = {BRICK: Decimal("1000")}


def line(resource_id: int, quantity: str, line_id: int = 1) -> PurchasedLine:
    return PurchasedLine(line_id=line_id, resource_id=resource_id, quantity=Decimal(quantity))


def only(earned: tuple[EarnedPoints, ...]) -> EarnedPoints:
    (one,) = earned
    return one


# --- the four cases -----------------------------------------------------------


def test_the_same_material_in_a_similar_quantity_is_worth_the_most():
    earned = only(rate([line(BRICK, "1200")], LAST_TIME, bought_before=True))

    assert (earned.rule, earned.points) == (SAME_MATERIAL_SIMILAR_QUANTITY, 10)
    assert earned.previous_quantity == Decimal("1000")


def test_the_same_material_in_another_quantity_is_worth_less():
    earned = only(rate([line(BRICK, "4000")], LAST_TIME, bought_before=True))

    assert (earned.rule, earned.points) == (SAME_MATERIAL, 6)
    # Still says what it was compared against, so the history can explain it.
    assert earned.previous_quantity == Decimal("1000")


def test_a_material_never_bought_from_this_supplier_is_worth_less_still():
    earned = only(rate([line(CEMENT, "30")], LAST_TIME, bought_before=True))

    assert (earned.rule, earned.points) == (SAME_SUPPLIER, 3)
    assert earned.previous_quantity is None


def test_the_first_purchase_from_a_supplier_is_worth_nothing():
    earned = only(rate([line(BRICK, "1000")], {}, bought_before=False))

    assert (earned.rule, earned.points) == (FIRST_PURCHASE, 0)
    assert earned.previous_quantity is None


# --- the edge of "similar" ----------------------------------------------------


@pytest.mark.parametrize("quantity", ["500", "1000", "1500", "999.999", "1000.001"])
def test_within_half_of_last_time_counts_as_similar(quantity):
    """The borders included: half as much and half again are both "like last time"."""
    earned = only(rate([line(BRICK, quantity)], LAST_TIME, bought_before=True))

    assert earned.rule == SAME_MATERIAL_SIMILAR_QUANTITY


@pytest.mark.parametrize("quantity", ["499.999", "1500.001", "1", "100000"])
def test_past_half_of_last_time_is_only_the_same_material(quantity):
    earned = only(rate([line(BRICK, quantity)], LAST_TIME, bought_before=True))

    assert earned.rule == SAME_MATERIAL


def test_similarity_is_measured_against_last_time_and_not_the_other_way_round():
    """10 against 1,000 is not similar; 1,000 against 10 is not either. The
    tolerance is half of what came last time, so it is not symmetric."""
    assert is_similar(Decimal("10"), Decimal("1000")) is False
    assert is_similar(Decimal("1000"), Decimal("10")) is False
    assert is_similar(Decimal("14"), Decimal("10")) is True


# --- a whole order ------------------------------------------------------------


def test_every_line_of_a_first_purchase_earns_nothing():
    """The lines of one order are never compared with each other: the second
    brick line is not "the same material as the first one"."""
    earned = rate(
        [line(BRICK, "1000", 1), line(CEMENT, "30", 2), line(SAND, "5", 3)],
        {},
        bought_before=False,
    )

    assert [one.rule for one in earned] == [FIRST_PURCHASE] * 3
    assert {one.points for one in earned} == {0}


def test_an_order_mixes_its_cases_line_by_line():
    earned = rate(
        [line(BRICK, "1100", 1), line(CEMENT, "9000", 2), line(SAND, "5", 3)],
        {BRICK: Decimal("1000"), CEMENT: Decimal("30")},
        bought_before=True,
    )

    assert [(one.line_id, one.rule, one.points) for one in earned] == [
        (1, SAME_MATERIAL_SIMILAR_QUANTITY, 10),
        (2, SAME_MATERIAL, 6),
        (3, SAME_SUPPLIER, 3),
    ]


def test_an_order_with_no_lines_earns_nothing():
    assert rate([], LAST_TIME, bought_before=True) == ()


def test_what_arrived_travels_with_the_points():
    """The quantity is kept on the entry, so the history shows what was bought."""
    earned = only(rate([line(BRICK, "1200.500")], LAST_TIME, bought_before=True))

    assert earned.quantity == Decimal("1200.500")
    assert earned.resource_id == BRICK


def test_a_firm_that_buys_often_is_not_a_first_purchase():
    """Which is why bought_before is asked for and not read off the map: an
    empty history of materials also describes a regular customer."""
    earned = only(rate([line(SAND, "5")], {}, bought_before=True))

    assert (earned.rule, earned.points) == (SAME_SUPPLIER, 3)


def test_the_four_rules_are_worth_what_adr_012_says():
    assert POINTS == {
        SAME_MATERIAL_SIMILAR_QUANTITY: 10,
        SAME_MATERIAL: 6,
        SAME_SUPPLIER: 3,
        FIRST_PURCHASE: 0,
    }


# --- levels (HU-24, ADR-012 section 5) ----------------------------------------
#
# Bronce from 0, Plata from 50, Oro from 150, Platino from 400.


@pytest.mark.parametrize(
    ("points", "level"),
    [
        (0, "bronze"),
        (49, "bronze"),
        (50, "silver"),
        (149, "silver"),
        (150, "gold"),
        (399, "gold"),
        (400, "platinum"),
        (10_000, "platinum"),
    ],
)
def test_a_total_reaches_the_level_its_threshold_allows(points, level):
    assert level_for(points).level == level


def test_nothing_earned_is_the_first_level_and_not_none():
    """A firm that has received no order is Bronce at zero, which is what the
    empty state of the screen is drawn around."""
    standing = level_for(0)

    assert (standing.level, standing.points, standing.level_from) == ("bronze", 0, 0)


def test_a_level_says_how_far_the_next_one_is():
    standing = level_for(60)

    assert (standing.level, standing.next_level) == ("silver", "gold")
    assert (standing.next_level_at, standing.points_to_next) == (150, 90)


def test_the_level_a_total_just_reached_needs_nothing_more_to_reach_it():
    """At exactly the threshold the bar is at the start of the new level, not at
    the end of the old one."""
    standing = level_for(150)

    assert (standing.level, standing.level_from) == ("gold", 150)
    assert standing.points_to_next == 250


def test_the_top_level_has_nothing_left_to_reach():
    standing = level_for(400)

    assert standing.level == "platinum"
    assert (standing.next_level, standing.next_level_at, standing.points_to_next) == (
        None,
        None,
        None,
    )


def test_the_levels_start_where_adr_012_says():
    assert LEVELS == (("bronze", 0), ("silver", 50), ("gold", 150), ("platinum", 400))
