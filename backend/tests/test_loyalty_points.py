"""The points an order earns when it is received (HU-23, ADR-012 sections 2 and 4).

The rule itself is tested without a database in test_loyalty.py. This file is
about the other half: that the entries are written at the right moment, against
the right previous purchase, and exactly once.

HU-23 has no routes of its own — reading the points is HU-24 — so the entries are
read straight off the table.

The wall is 500 m2 here, not the 120 of the order tests, so there is room to buy
bricks several times over: 500 m2 take 30,000 bricks and 125 bags of cement.
"""

import pytest
from sqlalchemy import text

from app.core.clock import today

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"


@pytest.fixture
def owner(world, auth_header) -> dict[str, str]:
    """The firm's owner: holds purchase_order.manage and project.view_all."""
    return auth_header(world.account_a)


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "500")


@pytest.fixture
def norte(world, add_supplier, add_price) -> int:
    supplier = add_supplier(world.firm_a, "Corralón Norte")
    add_price(world.firm_a, supplier, BRICK, "220.00")
    add_price(world.firm_a, supplier, CEMENT, "15500.00")
    return supplier


# --- driving the real path ----------------------------------------------------


def order_url(firm_id: int, order_id: int) -> str:
    return f"/firms/{firm_id}/purchase-orders/{order_id}"


def issued_order(
    client, headers, resource_id, quantities: dict[str, str], *, firm: int, project: int
) -> tuple[str, dict[str, int]]:
    """Generate an order for these materials, set the quantities and issue it.

    Answers with the order's url and its line ids by material name, which is
    what the callers need to receive it.
    """
    generated = client.post(
        f"/firms/{firm}/projects/{project}/purchase-orders/generate",
        json={"items": [{"resource_id": resource_id[name]} for name in quantities]},
        headers=headers,
    )
    assert generated.status_code == 200, generated.text
    url = order_url(firm, generated.json()["orders"][0]["id"])

    for line in client.get(url, headers=headers).json()["lines"]:
        patched = client.patch(
            f"{url}/lines/{line['id']}",
            json={"quantity": quantities[line["resource"]["name"]]},
            headers=headers,
        )
        assert patched.status_code == 200, patched.text

    assert client.post(f"{url}/issue", headers=headers).status_code == 200
    lines = {
        line["resource"]["name"]: line["id"]
        for line in client.get(url, headers=headers).json()["lines"]
    }
    return url, lines


def receive(client, headers, url: str, lines: dict[int, str]) -> dict:
    """Register a delivery of these quantities, by line id."""
    response = client.post(
        f"{url}/receipts",
        json={
            "received_on": str(today()),
            "lines": [
                {"line_id": line_id, "quantity": quantity, "actual_cost": "1000"}
                for line_id, quantity in lines.items()
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def buy(
    client, world, headers, resource_id, quantities: dict[str, str], *, firm=None, project=None
) -> dict:
    """The whole path a purchase takes: generated, issued and received whole.

    What is under test hangs off the last step, so every test that needs a
    completed purchase goes through all of it rather than writing rows by hand.
    """
    firm_id = firm or world.firm_a
    url, lines = issued_order(
        client, headers, resource_id, quantities, firm=firm_id, project=project or world.project_a
    )
    body = receive(
        client, headers, url, {lines[name]: quantity for name, quantity in quantities.items()}
    )
    assert body["status"] == "received", body["status"]
    return body


# --- reading the entries, which HU-23 gives no route for ----------------------


def entries(db, firm_id: int) -> list[dict]:
    """Every entry of a firm, oldest first, with its material's name."""
    rows = db.execute(
        text(
            "SELECT resource.name AS material, entry.rule, entry.points,"
            "       entry.quantity, entry.previous_quantity"
            "  FROM firm_points_entry AS entry"
            "  JOIN resource ON resource.id = entry.resource_id"
            " WHERE entry.firm_id = :firm"
            " ORDER BY entry.id"
        ),
        {"firm": firm_id},
    ).mappings()
    return [dict(row) for row in rows]


def rules(db, firm_id: int) -> list[tuple[str, str, int]]:
    return [(one["material"], one["rule"], one["points"]) for one in entries(db, firm_id)]


def rules_of(db, firm_id: int, *, last: int) -> list[tuple[str, str, int]]:
    """The last `last` entries, sorted, for assertions about one order's lines.

    Entries are written in the order the order's lines are read, and those come
    out by material name, not in the order they were asked for. Which line of an
    order earned first means nothing, so the assertion sorts and so does the
    expectation.
    """
    return sorted(rules(db, firm_id)[-last:])


# --- the four cases, through the real path ------------------------------------


def test_a_first_order_earns_nothing_and_says_why(
    client, db, world, wall, norte, owner, resource_id
):
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    assert rules(db, world.firm_a) == [(BRICK, "first_purchase", 0)]
    assert entries(db, world.firm_a)[0]["previous_quantity"] is None


def test_the_same_material_in_a_similar_quantity_earns_ten(
    client, db, world, wall, norte, owner, resource_id
):
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    buy(client, world, owner, resource_id, {BRICK: "1200"})

    assert rules(db, world.firm_a)[-1] == (BRICK, "same_material_similar_quantity", 10)
    assert entries(db, world.firm_a)[-1]["previous_quantity"] == 1000


def test_the_same_material_in_another_quantity_earns_six(
    client, db, world, wall, norte, owner, resource_id
):
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    buy(client, world, owner, resource_id, {BRICK: "9000"})

    assert rules(db, world.firm_a)[-1] == (BRICK, "same_material", 6)


def test_a_material_never_bought_from_that_supplier_earns_three(
    client, db, world, wall, norte, owner, resource_id
):
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    buy(client, world, owner, resource_id, {CEMENT: "30"})

    assert rules(db, world.firm_a)[-1] == (CEMENT, "same_supplier", 3)


def test_an_order_earns_line_by_line(client, db, world, wall, norte, owner, resource_id):
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    buy(client, world, owner, resource_id, {BRICK: "1100", CEMENT: "30"})

    assert rules_of(db, world.firm_a, last=2) == sorted(
        [
            (BRICK, "same_material_similar_quantity", 10),
            (CEMENT, "same_supplier", 3),
        ]
    )


def test_every_line_of_a_first_order_earns_nothing(
    client, db, world, wall, norte, owner, resource_id
):
    """The lines of one order are never compared with each other."""
    buy(client, world, owner, resource_id, {BRICK: "1000", CEMENT: "30"})

    assert rules_of(db, world.firm_a, last=2) == sorted(
        [
            (BRICK, "first_purchase", 0),
            (CEMENT, "first_purchase", 0),
        ]
    )


# --- which purchase counts as the previous one --------------------------------


def test_the_previous_purchase_is_the_last_order_that_had_that_material(
    client, db, world, wall, norte, owner, resource_id
):
    """Bricks, then only cement, then bricks again: the bricks are compared with
    the first order and not treated as never bought (ADR-012 section 3)."""
    buy(client, world, owner, resource_id, {BRICK: "1000"})
    buy(client, world, owner, resource_id, {CEMENT: "30"})

    buy(client, world, owner, resource_id, {BRICK: "1200"})

    assert rules(db, world.firm_a)[-1] == (BRICK, "same_material_similar_quantity", 10)
    assert entries(db, world.firm_a)[-1]["previous_quantity"] == 1000


def test_the_previous_purchase_is_the_most_recent_one(
    client, db, world, wall, norte, owner, resource_id
):
    """Three orders of bricks: the third is compared with the second, so 2,500
    after 2,000 is similar even though it is far from the first 1,000."""
    buy(client, world, owner, resource_id, {BRICK: "1000"})
    buy(client, world, owner, resource_id, {BRICK: "2000"})

    buy(client, world, owner, resource_id, {BRICK: "2500"})

    assert rules(db, world.firm_a)[-1] == (BRICK, "same_material_similar_quantity", 10)
    assert entries(db, world.firm_a)[-1]["previous_quantity"] == 2000


def test_a_purchase_for_another_work_counts_as_a_previous_purchase(
    client,
    db,
    world,
    wall,
    norte,
    owner,
    resource_id,
    recipe_id,
    new_project,
    add_takeoff_line,
):
    """The points are the firm's, so what was bought for one work counts for the
    next: ADR-012 section 3 compares "de cualquier obra"."""
    other = new_project(world.firm_a, world.account_a, "Casa Sur de Norte")
    add_takeoff_line(other, world.firm_a, recipe_id[WALL], "500")
    buy(client, world, owner, resource_id, {BRICK: "1000"})

    buy(client, world, owner, resource_id, {BRICK: "1200"}, project=other)

    assert rules(db, world.firm_a)[-1] == (BRICK, "same_material_similar_quantity", 10)


def test_another_firms_purchase_is_not_a_previous_purchase(
    client,
    db,
    world,
    wall,
    norte,
    owner,
    resource_id,
    recipe_id,
    add_supplier,
    add_price,
    add_takeoff_line,
    auth_header,
):
    """Firm B buys the same material from its own supplier, and firm A's first
    order is still a first purchase: each firm's history is its own."""
    sur = add_supplier(world.firm_b, "Corralón Sur")
    add_price(world.firm_b, sur, BRICK, "225.00")
    add_takeoff_line(world.project_b, world.firm_b, recipe_id[WALL], "500")
    buy(
        client,
        world,
        auth_header(world.account_b),
        resource_id,
        {BRICK: "1000"},
        firm=world.firm_b,
        project=world.project_b,
    )

    buy(client, world, owner, resource_id, {BRICK: "1000"})

    assert rules(db, world.firm_a) == [(BRICK, "first_purchase", 0)]
    assert rules(db, world.firm_b) == [(BRICK, "first_purchase", 0)]


# --- when the points are written ----------------------------------------------


def test_a_cancelled_order_earns_nothing(client, db, world, wall, norte, owner, resource_id):
    url, _ = issued_order(
        client,
        owner,
        resource_id,
        {BRICK: "1000"},
        firm=world.firm_a,
        project=world.project_a,
    )

    assert client.post(f"{url}/cancel", headers=owner).status_code == 200
    assert entries(db, world.firm_a) == []


def test_a_partial_delivery_earns_nothing_until_it_is_complete(
    client, db, world, wall, norte, owner, resource_id
):
    url, lines = issued_order(
        client,
        owner,
        resource_id,
        {BRICK: "1000"},
        firm=world.firm_a,
        project=world.project_a,
    )
    brick = lines[BRICK]

    receive(client, owner, url, {brick: "400"})
    assert entries(db, world.firm_a) == []

    receive(client, owner, url, {brick: "600"})
    assert rules(db, world.firm_a) == [(BRICK, "first_purchase", 0)]


def test_an_order_earns_once_even_after_a_delivery_was_reloaded(
    client, db, world, wall, norte, owner, resource_id
):
    """A delivery cancelled and loaded again walks the order out of received and
    back in, and the line ends up with one entry (ADR-012 section 8, rule 5).

    That an order already rated is left alone is the service's guard, and the
    unique index behind it; the index itself is tested in test_schema_invariants.
    """
    url, lines = issued_order(
        client,
        owner,
        resource_id,
        {BRICK: "1000"},
        firm=world.firm_a,
        project=world.project_a,
    )
    brick = lines[BRICK]
    partial = receive(client, owner, url, {brick: "400"})
    client.post(f"{url}/receipts/{partial['receipts'][0]['id']}/deactivate", headers=owner)

    receive(client, owner, url, {brick: "1000"})

    assert rules(db, world.firm_a) == [(BRICK, "first_purchase", 0)]


def test_the_entry_keeps_the_order_the_line_and_the_supplier(
    client, db, world, wall, norte, owner, resource_id
):
    """So the history of HU-24 can name the order, the work and the supplier."""
    order = buy(client, world, owner, resource_id, {BRICK: "1000"})

    row = (
        db.execute(
            text(
                "SELECT purchase_order_id, purchase_order_line_id, supplier_id, quantity"
                "  FROM firm_points_entry WHERE firm_id = :firm"
            ),
            {"firm": world.firm_a},
        )
        .mappings()
        .one()
    )

    assert row["purchase_order_id"] == order["id"]
    assert row["purchase_order_line_id"] == order["lines"][0]["id"]
    assert row["supplier_id"] == norte
    assert row["quantity"] == 1000


class TestLoyaltyEndpoint:
    """The firm's level and history over HTTP (HU-24, ADR-012 section 7).

    The levels themselves are tested without a database in test_loyalty.py. This
    is about what the screen receives: the total, the history with everything it
    has to explain, who gets in, and what an untouched firm answers.
    """

    def url(self, world) -> str:
        return f"/firms/{world.firm_a}/loyalty"

    def read(self, client, world, headers) -> dict:
        response = client.get(self.url(world), headers=headers)
        assert response.status_code == 200, response.text
        return response.json()

    def test_a_firm_that_received_nothing_is_bronze_at_zero(self, client, world, owner):
        body = self.read(client, world, owner)

        assert body["firm"]["points"] == 0
        assert body["firm"]["level"] == "bronze"
        assert body["firm"]["next_level"] == "silver"
        assert body["history"] == []

    def test_the_points_are_the_sum_of_the_entries(
        self, client, world, wall, norte, owner, resource_id
    ):
        """A first order earns nothing, and buying the same material again in a
        similar quantity earns ten: the total is 10, which is still Bronce."""
        buy(client, world, owner, resource_id, {BRICK: "1000"})
        buy(client, world, owner, resource_id, {BRICK: "1200"})

        body = self.read(client, world, owner)

        assert body["firm"]["points"] == 10
        assert body["firm"]["level"] == "bronze"
        assert body["firm"]["points_to_next"] == 40

    def test_the_history_explains_every_entry(self, client, world, wall, norte, owner, resource_id):
        buy(client, world, owner, resource_id, {BRICK: "1000"})
        order = buy(client, world, owner, resource_id, {BRICK: "1200"})

        newest, _ = self.read(client, world, owner)["history"]

        assert newest["rule"] == "same_material_similar_quantity"
        assert newest["points"] == 10
        assert newest["order"] == {"id": order["id"], "number": order["number"]}
        assert newest["project"]["name"] == "Casa Norte"
        assert newest["supplier"]["name"] == "Corralón Norte"
        assert newest["resource"]["name"] == BRICK
        assert newest["unit"]["abbreviation"] != ""
        assert (newest["quantity"], newest["previous_quantity"]) == ("1200.000", "1000.000")

    def test_the_history_is_newest_first(self, client, world, wall, norte, owner, resource_id):
        buy(client, world, owner, resource_id, {BRICK: "1000"})
        buy(client, world, owner, resource_id, {CEMENT: "30"})

        history = self.read(client, world, owner)["history"]

        assert [entry["resource"]["name"] for entry in history] == [CEMENT, BRICK]

    def test_an_entry_that_compared_nothing_says_so(
        self, client, world, wall, norte, owner, resource_id
    ):
        buy(client, world, owner, resource_id, {BRICK: "1000"})

        (only,) = self.read(client, world, owner)["history"]

        assert only["rule"] == "first_purchase"
        assert only["previous_quantity"] is None

    def test_an_architect_reads_the_level(
        self, client, world, wall, norte, owner, resource_id, auth_header
    ):
        buy(client, world, owner, resource_id, {BRICK: "1000"})

        body = self.read(client, world, auth_header(world.account_a2))

        assert len(body["history"]) == 1

    def test_the_client_does_not_see_this_section(self, client, world, new_member, auth_header):
        headers = auth_header(new_member(world.firm_a, "clara@test.com", "client"))

        assert client.get(self.url(world), headers=headers).status_code == 403

    def test_another_firm_reads_only_its_own(
        self, client, world, wall, norte, owner, resource_id, auth_header
    ):
        buy(client, world, owner, resource_id, {BRICK: "1000"})
        buy(client, world, owner, resource_id, {BRICK: "1200"})

        response = client.get(
            f"/firms/{world.firm_b}/loyalty", headers=auth_header(world.account_b)
        )

        assert response.status_code == 200
        assert response.json() == {
            "firm": {
                "points": 0,
                "level": "bronze",
                "level_from": 0,
                "next_level": "silver",
                "next_level_at": 50,
                "points_to_next": 50,
            },
            "history": [],
        }


class TestSupplierLevel:
    """The firm's level with one supplier, on its card (HU-24)."""

    def card(self, client, world, headers, supplier_id: int) -> dict:
        response = client.get(f"/firms/{world.firm_a}/suppliers/{supplier_id}", headers=headers)
        assert response.status_code == 200, response.text
        return response.json()

    def test_a_supplier_never_bought_from_is_bronze_at_zero(self, client, world, norte, owner):
        assert self.card(client, world, owner, norte)["level"] == {
            "points": 0,
            "level": "bronze",
            "level_from": 0,
            "next_level": "silver",
            "next_level_at": 50,
            "points_to_next": 50,
        }

    def test_the_level_counts_only_what_was_earned_with_that_supplier(
        self, client, world, wall, norte, owner, resource_id, add_supplier, add_price
    ):
        """Sur is on the firm's books too and has never been bought from, so
        what the orders to Norte earned does not show on Sur's card."""
        sur = add_supplier(world.firm_a, "Corralón Sur")
        add_price(world.firm_a, sur, CEMENT, "15000.00")
        buy(client, world, owner, resource_id, {BRICK: "1000"})
        buy(client, world, owner, resource_id, {BRICK: "1200"})

        assert self.card(client, world, owner, norte)["level"]["points"] == 10
        assert self.card(client, world, owner, sur)["level"]["points"] == 0
