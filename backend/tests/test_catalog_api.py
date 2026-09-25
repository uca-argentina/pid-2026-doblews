"""GET /firms/{firm_id}/catalog/...: the system catalogue as HU-4 shows it.

What the seed holds is pinned in test_catalog_seed.py; what is under test here
is what the endpoints make of it. That a recipe arrives with its lines and their
prices, that the numbers keep their decimals on the wire, that a deactivated row
drops out, and that every firm role holding catalog.view reads the same thing.

Someone outside the firm getting a 404 is not repeated here: the isolation suite
in test_route_permissions.py walks these routes like every other.

Ana owns firm A; Clara is a firm client of A.
"""

import pytest
from sqlalchemy import text

WALL = "Pared de ladrillo común 15cm"
BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"


def recipes(client, firm_id, headers):
    return client.get(f"/firms/{firm_id}/catalog/recipes", headers=headers)


def resources(client, firm_id, headers):
    return client.get(f"/firms/{firm_id}/catalog/resources", headers=headers)


@pytest.fixture
def clara(world, new_member):
    return new_member(world.firm_a, "clara@test.com", "client")


class TestRecipes:
    def test_lists_the_active_recipes_by_name(self, client, world, auth_header):
        response = recipes(client, world.firm_a, auth_header(world.account_a))

        assert response.status_code == 200
        names = [recipe["name"] for recipe in response.json()]
        assert names == [
            "Carpeta de cemento",
            "Contrapiso de cascote",
            WALL,
        ]

    def test_a_recipe_arrives_with_what_one_unit_of_it_takes(self, client, world, auth_header):
        """ADR-003's own example, typed out: 1 m2 of wall takes 60 bricks and a
        quarter of a bag of cement."""
        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        wall = next(recipe for recipe in body if recipe["name"] == WALL)

        assert wall["unit"] == {"code": "m2", "abbreviation": "m2"}
        assert wall["description"]
        lines = {line["name"]: line for line in wall["lines"]}
        assert lines[BRICK]["quantity_per_unit"] == "60.0000"
        assert lines[BRICK]["unit"]["code"] == "u"
        assert lines[CEMENT]["quantity_per_unit"] == "0.2500"
        assert lines[CEMENT]["unit"]["code"] == "bolsa"

    def test_each_line_carries_its_material_price_as_a_decimal_string(
        self, client, world, auth_header
    ):
        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        wall = next(recipe for recipe in body if recipe["name"] == WALL)
        brick = next(line for line in wall["lines"] if line["name"] == BRICK)

        assert brick["reference_price"] == "230.00"
        assert brick["currency"] == "ARS"

    def test_a_deactivated_recipe_is_not_offered(self, client, world, auth_header, db):
        db.execute(text("UPDATE recipe SET is_active = false WHERE name = :n"), {"n": WALL})

        body = recipes(client, world.firm_a, auth_header(world.account_a)).json()

        assert WALL not in {recipe["name"] for recipe in body}


class TestResources:
    def test_lists_the_active_resources_by_name_with_their_price(self, client, world, auth_header):
        response = resources(client, world.firm_a, auth_header(world.account_a))

        assert response.status_code == 200
        body = response.json()
        names = [resource["name"] for resource in body]
        assert names == sorted(names)
        assert len(body) == 10

        brick = next(resource for resource in body if resource["name"] == BRICK)
        assert brick["type"] == "material"
        assert brick["unit"] == {"code": "u", "abbreviation": "u"}
        assert brick["reference_price"] == "230.00"
        assert brick["currency"] == "ARS"
        assert brick["price_updated_at"]

    def test_a_deactivated_resource_is_not_listed(self, client, world, auth_header, db):
        db.execute(text("UPDATE resource SET is_active = false WHERE name = :n"), {"n": BRICK})

        body = resources(client, world.firm_a, auth_header(world.account_a)).json()

        assert BRICK not in {resource["name"] for resource in body}


class TestWhoReadsIt:
    def test_a_firm_client_reads_the_catalogue_prices_included(
        self, client, world, auth_header, clara
    ):
        """catalog.view is granted to client too (ADR-003 section 8). Reference
        prices are the platform's, not the firm's costs, so they are not hidden."""
        headers = auth_header(clara)

        assert recipes(client, world.firm_a, headers).status_code == 200
        body = resources(client, world.firm_a, headers).json()
        assert all(resource["reference_price"] for resource in body)

    def test_every_firm_reads_the_same_catalogue(self, client, world, auth_header):
        """Global to the platform: firm B's owner gets exactly what firm A's does."""
        from_a = recipes(client, world.firm_a, auth_header(world.account_a)).json()
        from_b = recipes(client, world.firm_b, auth_header(world.account_b)).json()

        assert from_a == from_b
