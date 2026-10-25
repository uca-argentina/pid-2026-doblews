"""Purchase order drafts over HTTP: the endpoints of HU-20 (ADR-011 sections 5 to 8).

The route audit in test_route_permissions.py already proves every one of these
declares a permission and keeps an outsider out. This file is about generating
drafts from the comparison, editing them while they are drafts and only then, who
of the firm gets in, and how "ya pedido" follows the drafts.

The wall of the budget's tests: 120 m2 take 7,200 bricks and 30 bags of cement.
Norte sells bricks cheaper per unit with shipping, Sur delivers free; for 7,200
bricks Norte wins (1,589,000 against 1,620,000), for 2,200 it still does
(489,000 against 495,000).
"""

import pytest
from sqlalchemy import text

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"
SAND = "Arena gruesa"
RUBBLE = "Cascote"
LABOR = "Oficial"


@pytest.fixture
def team(world, new_member, add_project_member):
    client = new_member(world.firm_a, "clara@test.com", "client")
    bystander = new_member(world.firm_a, "otto@test.com", "architect")
    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, client, world.firm_a, "client")
    return {
        "lead": world.account_a2,
        "owner": world.account_a,
        "client": client,
        "bystander": bystander,
        "stranger": world.account_b,
    }


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")


@pytest.fixture
def yards(world, add_supplier, add_price) -> dict[str, int]:
    norte = add_supplier(world.firm_a, "Corralón Norte")
    sur = add_supplier(world.firm_a, "Corralón Sur")
    add_price(world.firm_a, norte, BRICK, "220.00", "5000.00")
    add_price(world.firm_a, norte, CEMENT, "15500.00", "8000.00")
    add_price(world.firm_a, sur, BRICK, "225.00")
    return {"norte": norte, "sur": sur}


@pytest.fixture
def lead(team, auth_header) -> dict[str, str]:
    return auth_header(team["lead"])


def generate_url(world) -> str:
    return f"/firms/{world.firm_a}/projects/{world.project_a}/purchase-orders/generate"


def project_orders_url(world) -> str:
    return f"/firms/{world.firm_a}/projects/{world.project_a}/purchase-orders"


def order_url(world, order_id: int) -> str:
    return f"/firms/{world.firm_a}/purchase-orders/{order_id}"


def generate(client, world, headers, resource_id, *materials):
    response = client.post(
        generate_url(world),
        json={"resource_ids": [resource_id[name] for name in materials]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def lines(order: dict) -> dict[str, str]:
    """material name -> quantity, which is what most assertions compare."""
    return {line["resource"]["name"]: line["quantity"] for line in order["lines"]}


def ordered(client, world, headers) -> dict[str, str]:
    body = client.get(
        f"/firms/{world.firm_a}/projects/{world.project_a}/purchasing", headers=headers
    ).json()
    return {item["name"]: item["ordered_quantity"] for item in body["items"]}


class TestGenerate:
    def test_one_draft_per_supplier_with_the_cheapest(
        self, client, world, wall, yards, lead, resource_id
    ):
        body = generate(client, world, lead, resource_id, BRICK, CEMENT, SAND)

        (summary,) = body["orders"]
        assert (summary["supplier"]["name"], summary["status"], summary["number"]) == (
            "Corralón Norte",
            "draft",
            1,
        )
        assert summary["line_count"] == 2
        # 7,200 x 220 + 5,000 and 30 x 15,500 + 8,000.
        assert summary["estimated_total"] == "2062000.00"
        assert body["skipped"] == [
            {"resource_id": resource_id[SAND], "name": SAND, "reason": "no_supplier"}
        ]

    def test_the_quantity_is_what_the_work_still_needs(
        self, client, world, wall, yards, lead, resource_id
    ):
        (summary,) = generate(client, world, lead, resource_id, BRICK, CEMENT)["orders"]

        order = client.get(order_url(world, summary["id"]), headers=lead).json()
        assert lines(order) == {BRICK: "7200.000", CEMENT: "30.000"}

    def test_what_is_already_on_order_is_not_asked_again(
        self, client, world, wall, yards, lead, resource_id
    ):
        generate(client, world, lead, resource_id, BRICK)

        body = generate(client, world, lead, resource_id, BRICK)

        assert body["orders"] == []
        assert body["skipped"][0]["reason"] == "already_ordered"

    def test_the_rest_lands_on_the_same_draft_line(
        self, client, world, wall, yards, lead, resource_id
    ):
        """Lower the bricks to 5,000, generate again: the 2,200 left still go to
        Norte, whose draft already has bricks, so that line grows back."""
        (summary,) = generate(client, world, lead, resource_id, BRICK)["orders"]
        order = client.get(order_url(world, summary["id"]), headers=lead).json()
        line_id = order["lines"][0]["id"]
        client.patch(
            f"{order_url(world, summary['id'])}/lines/{line_id}",
            json={"quantity": "5000"},
            headers=lead,
        )

        (again,) = generate(client, world, lead, resource_id, BRICK)["orders"]

        assert again["id"] == summary["id"]
        assert lines(client.get(order_url(world, again["id"]), headers=lead).json()) == {
            BRICK: "7200.000"
        }

    def test_the_price_is_frozen_when_the_line_is_made(
        self, client, db, world, wall, yards, lead, resource_id
    ):
        (summary,) = generate(client, world, lead, resource_id, BRICK)["orders"]
        db.execute(
            text("UPDATE supplier_price SET unit_price = 999 WHERE supplier_id = :s"),
            {"s": yards["norte"]},
        )

        order = client.get(order_url(world, summary["id"]), headers=lead).json()
        assert order["lines"][0]["unit_price"] == "220.00"

    @pytest.mark.parametrize("material", [RUBBLE, LABOR])
    def test_only_materials_of_the_works_take_off(
        self, client, world, wall, yards, lead, resource_id, material
    ):
        """Rubble is a material but not in this wall; Oficial is labour."""
        response = client.post(
            generate_url(world), json={"resource_ids": [resource_id[material]]}, headers=lead
        )

        assert response.status_code == 422

    def test_an_empty_request_is_422(self, client, world, wall, lead):
        assert (
            client.post(generate_url(world), json={"resource_ids": []}, headers=lead).status_code
            == 422
        )

    def test_the_comparison_shows_what_is_on_order(
        self, client, world, wall, yards, lead, resource_id
    ):
        generate(client, world, lead, resource_id, BRICK)

        assert ordered(client, world, lead)[BRICK] == "7200.000"
        assert ordered(client, world, lead)[CEMENT] == "0"


class TestEditDraft:
    @pytest.fixture
    def draft(self, client, world, wall, yards, lead, resource_id) -> dict:
        (summary,) = generate(client, world, lead, resource_id, BRICK, CEMENT)["orders"]
        return client.get(order_url(world, summary["id"]), headers=lead).json()

    def line_id(self, order: dict, material: str) -> int:
        return next(line["id"] for line in order["lines"] if line["resource"]["name"] == material)

    def test_change_a_quantity(self, client, world, draft, lead):
        response = client.patch(
            f"{order_url(world, draft['id'])}/lines/{self.line_id(draft, CEMENT)}",
            json={"quantity": "12.5"},
            headers=lead,
        )

        assert response.status_code == 200
        assert lines(response.json())[CEMENT] == "12.500"

    @pytest.mark.parametrize("quantity", ["0", "-1", "1.2345"])
    def test_a_bad_quantity_is_422(self, client, world, draft, lead, quantity):
        response = client.patch(
            f"{order_url(world, draft['id'])}/lines/{self.line_id(draft, CEMENT)}",
            json={"quantity": quantity},
            headers=lead,
        )

        assert response.status_code == 422

    def test_move_a_line_to_another_supplier(self, client, world, draft, yards, add_price, lead):
        add_price(world.firm_a, yards["sur"], CEMENT, "15800.00")

        response = client.post(
            f"{order_url(world, draft['id'])}/lines/{self.line_id(draft, CEMENT)}/supplier",
            json={"supplier_id": yards["sur"]},
            headers=lead,
        )

        assert response.status_code == 200
        moved = response.json()
        assert (moved["supplier"]["name"], moved["number"]) == ("Corralón Sur", 2)
        assert moved["lines"][0]["unit_price"] == "15800.00"
        assert lines(client.get(order_url(world, draft["id"]), headers=lead).json()) == {
            BRICK: "7200.000"
        }

    def test_a_supplier_that_does_not_offer_it_is_422(self, client, world, draft, yards, lead):
        response = client.post(
            f"{order_url(world, draft['id'])}/lines/{self.line_id(draft, CEMENT)}/supplier",
            json={"supplier_id": yards["sur"]},
            headers=lead,
        )

        assert response.status_code == 422

    def test_remove_a_line_and_add_it_back(self, client, world, draft, lead, resource_id):
        removed = client.post(
            f"{order_url(world, draft['id'])}/lines/{self.line_id(draft, CEMENT)}/deactivate",
            headers=lead,
        )
        assert lines(removed.json()) == {BRICK: "7200.000"}

        added = client.post(
            f"{order_url(world, draft['id'])}/lines",
            json={"resource_id": resource_id[CEMENT], "quantity": "10"},
            headers=lead,
        )
        assert added.status_code == 200
        assert lines(added.json())[CEMENT] == "10.000"

    def test_a_material_already_in_the_order_is_409(self, client, world, draft, lead, resource_id):
        response = client.post(
            f"{order_url(world, draft['id'])}/lines",
            json={"resource_id": resource_id[BRICK], "quantity": "10"},
            headers=lead,
        )

        assert response.status_code == 409

    def test_a_material_outside_the_take_off_is_422(self, client, world, draft, lead, resource_id):
        response = client.post(
            f"{order_url(world, draft['id'])}/lines",
            json={"resource_id": resource_id[RUBBLE], "quantity": "10"},
            headers=lead,
        )

        assert response.status_code == 422

    def test_discard_gives_the_quantities_back(self, client, world, draft, lead, resource_id):
        response = client.post(f"{order_url(world, draft['id'])}/discard", headers=lead)

        assert response.status_code == 204
        assert client.get(order_url(world, draft["id"]), headers=lead).status_code == 404
        assert ordered(client, world, lead)[BRICK] == "0"

    def test_a_discarded_number_is_not_reused(self, client, world, draft, lead, resource_id):
        client.post(f"{order_url(world, draft['id'])}/discard", headers=lead)

        (again,) = generate(client, world, lead, resource_id, BRICK)["orders"]

        assert again["number"] == 2

    def test_only_a_draft_is_edited(self, client, db, world, draft, lead):
        db.execute(
            text(
                "UPDATE purchase_order SET status = 'issued', issued_at = now(), issued_by = :a"
                " WHERE id = :o"
            ),
            {"a": world.account_a, "o": draft["id"]},
        )
        url = order_url(world, draft["id"])

        assert (
            client.patch(
                f"{url}/lines/{self.line_id(draft, CEMENT)}", json={"quantity": "1"}, headers=lead
            ).status_code
            == 409
        )
        assert client.post(f"{url}/discard", headers=lead).status_code == 409

    def test_an_issued_order_is_not_reused_by_generate(
        self, client, db, world, draft, yards, lead, resource_id
    ):
        """Generating after issuing makes a new draft: an issued order never grows."""
        db.execute(
            text(
                "UPDATE purchase_order SET status = 'issued', issued_at = now(), issued_by = :a"
                " WHERE id = :o"
            ),
            {"a": world.account_a, "o": draft["id"]},
        )
        line_id = self.line_id(draft, CEMENT)
        db.execute(
            text("UPDATE purchase_order_line SET quantity = 10 WHERE id = :l"), {"l": line_id}
        )

        (fresh,) = generate(client, world, lead, resource_id, CEMENT)["orders"]

        assert fresh["id"] != draft["id"]
        assert lines(client.get(order_url(world, fresh["id"]), headers=lead).json()) == {
            CEMENT: "20.000"
        }


class TestWhoGetsIn:
    def test_the_lead_lists_the_works_drafts(self, client, world, wall, yards, lead, resource_id):
        generate(client, world, lead, resource_id, BRICK)

        response = client.get(
            project_orders_url(world), params={"order_status": "draft"}, headers=lead
        )

        assert response.status_code == 200
        assert [order["supplier"]["name"] for order in response.json()] == ["Corralón Norte"]

    def test_an_architect_off_the_work_manages_its_order_from_the_firm(
        self, client, world, wall, yards, lead, team, auth_header, resource_id
    ):
        """The permissions are firm-scope (ADR-011 section 6): the order is theirs to
        manage, though the work's own routes do not open to them."""
        (summary,) = generate(client, world, lead, resource_id, BRICK)["orders"]
        headers = auth_header(team["bystander"])

        assert client.get(order_url(world, summary["id"]), headers=headers).status_code == 200
        assert (
            client.post(f"{order_url(world, summary['id'])}/discard", headers=headers).status_code
            == 204
        )
        assert (
            client.post(
                generate_url(world), json={"resource_ids": [resource_id[BRICK]]}, headers=headers
            ).status_code
            == 404
        )

    def test_the_client_sees_no_order(
        self, client, world, wall, yards, lead, team, auth_header, resource_id
    ):
        (summary,) = generate(client, world, lead, resource_id, BRICK)["orders"]
        headers = auth_header(team["client"])

        assert client.get(order_url(world, summary["id"]), headers=headers).status_code == 403
        assert client.get(project_orders_url(world), headers=headers).status_code == 403
        assert (
            client.post(
                generate_url(world), json={"resource_ids": [resource_id[BRICK]]}, headers=headers
            ).status_code
            == 403
        )

    def test_another_firms_order_is_404(
        self, client, world, wall, yards, lead, team, auth_header, resource_id
    ):
        (summary,) = generate(client, world, lead, resource_id, BRICK)["orders"]

        response = client.get(
            f"/firms/{world.firm_b}/purchase-orders/{summary['id']}",
            headers=auth_header(team["stranger"]),
        )

        assert response.status_code == 404
