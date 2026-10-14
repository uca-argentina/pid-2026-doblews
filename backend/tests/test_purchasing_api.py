"""The two comparisons of HU-18 over HTTP (ADR-010 sections 4, 7 and 8).

The route audit in test_route_permissions.py already proves both declare a
permission and keep an outsider out. This file is about who of the firm gets in,
what each comparison shows, and which offers count: only live ones, of live
suppliers, of the firm, for materials the catalogue still has. The arithmetic is
pinned without a database in test_purchasing.py.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"
SAND = "Arena gruesa"
LABOR = "Oficial"


@pytest.fixture
def add_supplier(db):
    """A supplier of a firm, written behind the API's back like add_takeoff_line:
    a read is tested here, not HU-17's write path."""

    def _add(firm: int, name: str, is_active: bool = True) -> int:
        return db.execute(
            text(
                "INSERT INTO supplier (firm_id, name, is_active) VALUES (:f, :n, :a) RETURNING id"
            ),
            {"f": firm, "n": name, "a": is_active},
        ).scalar_one()

    return _add


@pytest.fixture
def add_price(db, resource_id):
    def _add(
        firm: int,
        supplier: int,
        material: str,
        unit_price: str,
        shipping: str = "0.00",
        is_active: bool = True,
    ) -> int:
        return db.execute(
            text(
                "INSERT INTO supplier_price"
                " (supplier_id, firm_id, resource_id, unit_price, shipping_cost, is_active)"
                " VALUES (:s, :f, :r, :p, :c, :a) RETURNING id"
            ),
            {
                "s": supplier,
                "f": firm,
                "r": resource_id[material],
                "p": unit_price,
                "c": shipping,
                "a": is_active,
            },
        ).scalar_one()

    return _add


@pytest.fixture
def team(world, new_member, add_project_member):
    """The cast of the budget's tests: what the guard of a work's costs lets in."""
    collaborator = new_member(world.firm_a, "carlos@test.com", "architect")
    client = new_member(world.firm_a, "clara@test.com", "client")
    bystander = new_member(world.firm_a, "otto@test.com", "architect")

    add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")
    add_project_member(world.project_a, collaborator, world.firm_a, "collaborator")
    add_project_member(world.project_a, client, world.firm_a, "client")

    return {
        "lead": world.account_a2,
        "collaborator": collaborator,
        "client": client,
        "owner": world.account_a,
        "bystander": bystander,
        "stranger": world.account_b,
    }


@pytest.fixture
def wall(world, recipe_id, add_takeoff_line) -> int:
    """120 m2 of wall on work A: 7,200 bricks at a reference price of 230."""
    return add_takeoff_line(world.project_a, world.firm_a, recipe_id[WALL], "120")


@pytest.fixture
def two_yards(world, add_supplier, add_price) -> dict[str, int]:
    """Two suppliers of firm A that both sell bricks.

    Norte is cheaper per brick and charges for delivery; Sur delivers free at a
    higher price. Which one wins depends on how many bricks: that is the point
    of comparing at a quantity (ADR-010 section 4).
    """
    norte = add_supplier(world.firm_a, "Corralón Norte")
    sur = add_supplier(world.firm_a, "Corralón Sur")
    add_price(world.firm_a, norte, BRICK, "220.00", "5000.00")
    add_price(world.firm_a, sur, BRICK, "225.00")
    return {"norte": norte, "sur": sur}


def compare_url(world) -> str:
    return f"/firms/{world.firm_a}/purchasing/compare"


def project_url(world, project_id: int | None = None) -> str:
    return f"/firms/{world.firm_a}/projects/{project_id or world.project_a}/purchasing"


def ranking(offers) -> list[tuple[str, str, bool]]:
    return [(found["supplier_name"], found["total"], found["cheapest"]) for found in offers]


def item(body, name: str) -> dict:
    return next(found for found in body["items"] if found["name"] == name)


class TestCompareMaterial:
    def test_every_offer_cheapest_first(self, client, world, two_yards, resource_id, auth_header):
        response = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK], "quantity": "10"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200
        body = response.json()
        assert ranking(body["offers"]) == [
            ("Corralón Sur", "2250.00", True),
            ("Corralón Norte", "7200.00", False),
        ]
        assert (body["name"], body["quantity"], body["unit"]["code"]) == (BRICK, "10", "u")
        assert (body["reference_price"], body["reference_total"]) == ("230.00", "2300.00")
        assert (body["currency"], body["has_suppliers"]) == ("ARS", True)

    def test_a_larger_quantity_can_change_the_winner(
        self, client, world, two_yards, resource_id, auth_header
    ):
        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK], "quantity": "7200"},
            headers=auth_header(world.account_a),
        ).json()

        assert ranking(body["offers"])[0] == ("Corralón Norte", "1589000.00", True)

    def test_the_quantity_defaults_to_one(self, client, world, two_yards, resource_id, auth_header):
        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK]},
            headers=auth_header(world.account_a),
        ).json()

        assert body["quantity"] == "1"
        assert ranking(body["offers"])[0] == ("Corralón Sur", "225.00", True)

    def test_a_tie_marks_both(
        self, client, world, two_yards, add_supplier, add_price, resource_id, auth_header
    ):
        este = add_supplier(world.firm_a, "Corralón Este")
        add_price(world.firm_a, este, BRICK, "220.00", "50.00")

        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK], "quantity": "10"},
            headers=auth_header(world.account_a),
        ).json()

        assert [found["cheapest"] for found in body["offers"]] == [True, True, False]

    def test_a_material_nobody_offers_has_no_offers(
        self, client, world, two_yards, resource_id, auth_header
    ):
        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[SAND]},
            headers=auth_header(world.account_a),
        ).json()

        assert body["offers"] == []
        assert body["has_suppliers"] is True

    def test_a_firm_without_suppliers_says_so(self, client, world, resource_id, auth_header):
        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK]},
            headers=auth_header(world.account_a),
        ).json()

        assert (body["offers"], body["has_suppliers"]) == ([], False)

    @pytest.mark.parametrize("quantity", ["0", "-1", "1.2345", "abc"])
    def test_a_bad_quantity_is_422(self, client, world, resource_id, auth_header, quantity):
        response = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK], "quantity": quantity},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422

    def test_labour_cannot_be_compared(self, client, world, resource_id, auth_header):
        """Not on any list (ADR-010 section 7, rule 1): 422, as when pricing it."""
        response = client.get(
            compare_url(world),
            params={"resource_id": resource_id[LABOR]},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422

    def test_a_missing_material_is_422(self, client, world, auth_header):
        response = client.get(
            compare_url(world),
            params={"resource_id": 999_999},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422


class TestWhichOffersCount:
    def get(self, client, world, resource_id, auth_header) -> list[str]:
        body = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK]},
            headers=auth_header(world.account_a),
        ).json()
        return [found["supplier_name"] for found in body["offers"]]

    def test_a_deactivated_supplier_is_out_with_its_list(
        self, client, db, world, two_yards, resource_id, auth_header
    ):
        db.execute(
            text("UPDATE supplier SET is_active = false WHERE id = :s"), {"s": two_yards["sur"]}
        )

        assert self.get(client, world, resource_id, auth_header) == ["Corralón Norte"]

    def test_a_removed_row_is_out(self, client, db, world, two_yards, resource_id, auth_header):
        db.execute(
            text("UPDATE supplier_price SET is_active = false WHERE supplier_id = :s"),
            {"s": two_yards["norte"]},
        )

        assert self.get(client, world, resource_id, auth_header) == ["Corralón Sur"]

    def test_another_firms_supplier_never_shows(
        self, client, world, two_yards, add_supplier, add_price, resource_id, auth_header
    ):
        theirs = add_supplier(world.firm_b, "Corralón de B")
        add_price(world.firm_b, theirs, BRICK, "1.00")

        assert "Corralón de B" not in self.get(client, world, resource_id, auth_header)

    def test_a_material_the_catalogue_retired_is_no_longer_offered(
        self, client, db, world, wall, two_yards, resource_id, auth_header
    ):
        """Rule 2: the rows stay, but the material drops out of the comparison.
        The work still lists it, as "sin proveedor"."""
        db.execute(
            text("UPDATE resource SET is_active = false WHERE id = :r"), {"r": resource_id[BRICK]}
        )

        compared = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK]},
            headers=auth_header(world.account_a),
        )
        assert compared.status_code == 422

        body = client.get(project_url(world), headers=auth_header(world.account_a)).json()
        assert item(body, BRICK)["offers"] == []


class TestProjectPurchasing:
    def test_each_material_at_the_quantity_the_work_needs(
        self, client, world, team, wall, two_yards, auth_header
    ):
        response = client.get(project_url(world), headers=auth_header(team["lead"]))

        assert response.status_code == 200
        brick = item(response.json(), BRICK)
        assert brick["quantity"] == "7200.000"
        assert (brick["reference_price"], brick["reference_total"]) == ("230.00", "1656000.00")
        assert ranking(brick["offers"]) == [
            ("Corralón Norte", "1589000.00", True),
            ("Corralón Sur", "1620000.00", False),
        ]

    def test_only_materials_are_compared(self, client, world, team, wall, two_yards, auth_header):
        """The wall also takes hours of Oficial and Ayudante: nobody sells those."""
        body = client.get(project_url(world), headers=auth_header(team["lead"])).json()

        assert [found["name"] for found in body["items"]] == [
            SAND,
            "Cal hidratada (bolsa 25 kg)",
            CEMENT,
            BRICK,
        ]

    def test_a_material_nobody_offers_keeps_its_reference_cost(
        self, client, world, team, wall, two_yards, auth_header
    ):
        """Shown as "sin proveedor": no offers, and what the budget counts it at."""
        cement = item(
            client.get(project_url(world), headers=auth_header(team["lead"])).json(), CEMENT
        )

        assert cement["offers"] == []
        assert cement["reference_total"] == "480000.00"

    def test_the_reference_costs_are_the_budgets(
        self, client, world, team, wall, two_yards, auth_header
    ):
        """The same rows as HU-11, so the two screens agree to the cent."""
        purchasing = client.get(project_url(world), headers=auth_header(team["lead"])).json()
        budget = client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/budget",
            headers=auth_header(team["lead"]),
        ).json()

        materials = next(found for found in budget["groups"] if found["type"] == "material")
        assert {found["name"]: found["reference_total"] for found in purchasing["items"]} == {
            found["name"]: found["subtotal"] for found in materials["items"]
        }

    def test_there_is_no_grand_total(self, client, world, team, wall, two_yards, auth_header):
        """HU-18 leaves an optimal purchase of the whole work out."""
        body = client.get(project_url(world), headers=auth_header(team["lead"])).json()

        assert set(body) == {"items", "currency", "has_suppliers"}

    def test_a_work_with_no_take_off_has_no_items(self, client, world, team, auth_header):
        body = client.get(project_url(world), headers=auth_header(team["lead"])).json()

        assert body == {"items": [], "currency": "ARS", "has_suppliers": False}

    def test_the_budget_is_untouched(self, client, world, team, wall, two_yards, auth_header):
        """ADR-010 section 5: supplier prices feed the comparison and nothing else."""
        body = client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/budget",
            headers=auth_header(team["lead"]),
        ).json()

        assert body["total"] == "3877800.00"


class TestWhoMayRead:
    @pytest.mark.parametrize("role", ["lead", "collaborator", "owner"])
    def test_these_roles_read_the_works_purchasing(
        self, client, world, team, wall, auth_header, role
    ):
        """The owner is on no work and comes in through project.view_all."""
        response = client.get(project_url(world), headers=auth_header(team[role]))

        assert response.status_code == 200

    def test_the_client_sees_neither_comparison(
        self, client, world, team, wall, resource_id, auth_header
    ):
        headers = auth_header(team["client"])

        assert client.get(project_url(world), headers=headers).status_code == 403
        compared = client.get(
            compare_url(world), params={"resource_id": resource_id[BRICK]}, headers=headers
        )
        assert compared.status_code == 403

    def test_an_architect_of_the_firm_compares_materials(
        self, client, world, team, resource_id, auth_header
    ):
        response = client.get(
            compare_url(world),
            params={"resource_id": resource_id[BRICK]},
            headers=auth_header(team["bystander"]),
        )

        assert response.status_code == 200

    @pytest.mark.parametrize("role", ["bystander", "stranger"])
    def test_someone_off_the_work_gets_404(self, client, world, team, wall, auth_header, role):
        response = client.get(project_url(world), headers=auth_header(team[role]))

        assert response.status_code == 404

    def test_another_firms_work_is_404(self, client, world, team, auth_header):
        response = client.get(
            project_url(world, world.project_b), headers=auth_header(team["owner"])
        )

        assert response.status_code == 404


def test_offers_are_decimal_strings(client, world, two_yards, resource_id, auth_header):
    """Money travels as strings, like every other amount of the API."""
    body = client.get(
        compare_url(world),
        params={"resource_id": resource_id[BRICK]},
        headers=auth_header(world.account_a),
    ).json()

    assert Decimal(body["offers"][0]["unit_price"]) == Decimal("225.00")
