"""/firms/{firm_id}/suppliers: the endpoints of HU-17 (ADR-010 section 8).

The route audit in test_route_permissions.py already proves every one of these
declares a permission, resolves the roster, and answers an outsider with 404 on its
GETs. This file is about what each endpoint does for the people allowed in, who is
not (the client), and the status codes suppliers.py's rules map to. The rules
themselves are pinned in test_suppliers_service.py; here they are only followed as
far as the response.
"""

import pytest

BRICK = "Ladrillo común"
CEMENT = "Cemento portland (bolsa 50 kg)"
LABOR = "Oficial"


@pytest.fixture
def url(world) -> str:
    return f"/firms/{world.firm_a}/suppliers"


@pytest.fixture
def owner(world, auth_header) -> dict[str, str]:
    return auth_header(world.account_a)


@pytest.fixture
def architect(world, auth_header) -> dict[str, str]:
    return auth_header(world.account_a2)


@pytest.fixture
def stranger(world, auth_header) -> dict[str, str]:
    """Bruno, owner of firm B: he belongs to a firm, just not this one."""
    return auth_header(world.account_b)


@pytest.fixture
def firm_client(world, new_member, auth_header) -> dict[str, str]:
    """A client of firm A: on its roster, without any supplier permission."""
    return auth_header(new_member(world.firm_a, "cliente@test.com", "client"))


def supplier_body(**overrides) -> dict:
    return {"name": "Corralón Norte", "contact_name": "Marta", "phone": "388 555 0101"} | overrides


def create(client, url, headers, **overrides) -> dict:
    response = client.post(url, json=supplier_body(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def add_price(client, url, headers, supplier_id, resource_id, material=BRICK, **overrides):
    body = {
        "resource_id": resource_id[material],
        "unit_price": "230.00",
        "shipping_cost": "1500.00",
    }
    return client.post(f"{url}/{supplier_id}/prices", json=body | overrides, headers=headers)


class TestWhoGetsIn:
    def test_anonymous_gets_401(self, client, url):
        assert client.get(url).status_code == 401

    def test_an_architect_reads_and_writes(self, client, url, architect):
        assert client.post(url, json=supplier_body(), headers=architect).status_code == 201
        assert client.get(url, headers=architect).status_code == 200

    def test_the_client_of_the_firm_does_not_see_the_section(self, client, url, firm_client, owner):
        """403 and not an empty list: it is the firm's costs (ADR-010 section 6)."""
        created = create(client, url, owner)

        assert client.get(url, headers=firm_client).status_code == 403
        assert client.get(f"{url}/{created['id']}", headers=firm_client).status_code == 403
        assert client.get(f"{url}/{created['id']}/prices", headers=firm_client).status_code == 403
        assert client.post(url, json=supplier_body(), headers=firm_client).status_code == 403

    def test_a_stranger_gets_404_even_when_writing(self, client, url, stranger):
        assert client.post(url, json=supplier_body(), headers=stranger).status_code == 404


class TestSuppliers:
    def test_create_answers_201_with_the_row(self, client, url, owner):
        created = create(client, url, owner, contact_email="marta@norte.com")

        assert created | {"id": 0} == {
            "id": 0,
            "name": "Corralón Norte",
            "contact_name": "Marta",
            "contact_email": "marta@norte.com",
            "phone": "388 555 0101",
            "address": None,
            "price_count": 0,
        }

    def test_only_the_name_is_required(self, client, url, owner):
        response = client.post(url, json={"name": "  Corralón Sur  "}, headers=owner)

        assert response.status_code == 201
        assert response.json()["name"] == "Corralón Sur"
        assert response.json()["contact_name"] is None

    def test_a_blank_optional_field_is_stored_as_nothing(self, client, url, owner):
        created = create(client, url, owner, contact_name="   ", contact_email="")

        assert (created["contact_name"], created["contact_email"]) == (None, None)

    @pytest.mark.parametrize(
        "bad",
        [
            {"name": "   "},
            {"name": "x" * 151},
            {"contact_email": "no-es-un-email"},
            {"phone": "1" * 31},
        ],
    )
    def test_a_malformed_body_is_422(self, client, url, owner, bad):
        assert client.post(url, json=supplier_body(**bad), headers=owner).status_code == 422

    def test_a_repeated_name_is_409(self, client, url, owner):
        create(client, url, owner)

        response = client.post(url, json=supplier_body(name="CORRALÓN NORTE"), headers=owner)

        assert response.status_code == 409

    def test_the_list_is_by_name_with_the_length_of_each_list(
        self, client, url, owner, resource_id
    ):
        zeta = create(client, url, owner, name="Zeta")
        create(client, url, owner, name="alfa")
        add_price(client, url, owner, zeta["id"], resource_id)

        rows = client.get(url, headers=owner).json()

        assert [(row["name"], row["price_count"]) for row in rows] == [("alfa", 0), ("Zeta", 1)]

    def test_the_list_never_shows_another_firm_s_suppliers(
        self, client, world, url, owner, stranger
    ):
        create(client, f"/firms/{world.firm_b}/suppliers", stranger, name="De otro estudio")

        assert client.get(url, headers=owner).json() == []

    def test_read_one_comes_with_its_list(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        add_price(client, url, owner, created["id"], resource_id)

        body = client.get(f"{url}/{created['id']}", headers=owner).json()

        assert body["name"] == "Corralón Norte"
        assert body["price_count"] == 1
        assert [row["resource"]["name"] for row in body["prices"]] == [BRICK]

    def test_patch_changes_what_was_sent_and_keeps_the_rest(self, client, url, owner):
        created = create(client, url, owner)

        response = client.patch(
            f"{url}/{created['id']}", json={"phone": "388 555 0202"}, headers=owner
        )

        assert response.status_code == 200
        assert response.json()["phone"] == "388 555 0202"
        assert response.json()["contact_name"] == "Marta"

    def test_patch_with_null_clears_an_optional_field(self, client, url, owner):
        created = create(client, url, owner)

        response = client.patch(f"{url}/{created['id']}", json={"phone": None}, headers=owner)

        assert response.json()["phone"] is None

    def test_patch_cannot_clear_the_name(self, client, url, owner):
        created = create(client, url, owner)

        response = client.patch(f"{url}/{created['id']}", json={"name": None}, headers=owner)

        assert response.status_code == 422

    def test_patch_to_a_name_another_supplier_uses_is_409(self, client, url, owner):
        create(client, url, owner, name="Corralón Sur")
        other = create(client, url, owner)

        response = client.patch(
            f"{url}/{other['id']}", json={"name": "Corralón Sur"}, headers=owner
        )

        assert response.status_code == 409

    def test_deactivate_answers_204_and_the_supplier_is_gone(self, client, url, owner):
        created = create(client, url, owner)

        assert client.post(f"{url}/{created['id']}/deactivate", headers=owner).status_code == 204

        assert client.get(f"{url}/{created['id']}", headers=owner).status_code == 404
        assert client.get(url, headers=owner).json() == []

    def test_there_is_no_way_to_delete_one(self, client, url, owner):
        created = create(client, url, owner)

        assert client.delete(f"{url}/{created['id']}", headers=owner).status_code == 405

    def test_another_firm_s_supplier_is_404_for_every_verb(
        self, client, world, url, owner, stranger
    ):
        theirs = create(client, f"/firms/{world.firm_b}/suppliers", stranger)
        target = f"{url}/{theirs['id']}"

        assert client.get(target, headers=owner).status_code == 404
        assert client.patch(target, json={"phone": "1"}, headers=owner).status_code == 404
        assert client.post(f"{target}/deactivate", headers=owner).status_code == 404
        assert client.get(f"{target}/prices", headers=owner).status_code == 404


class TestPrices:
    def test_add_answers_201_with_the_row_and_both_prices(
        self, client, url, owner, resource_id
    ):
        created = create(client, url, owner)

        response = add_price(client, url, owner, created["id"], resource_id)

        assert response.status_code == 201
        body = response.json()
        assert (body["unit_price"], body["shipping_cost"], body["currency"]) == (
            "230.00",
            "1500.00",
            "ARS",
        )
        # The supplier's price and the one the budget computes with, side by side.
        assert body["resource"]["name"] == BRICK
        assert body["resource"]["unit"]["abbreviation"]
        assert body["resource"]["reference_price"]
        assert body["price_updated_at"]

    def test_shipping_defaults_to_zero(self, client, url, owner, resource_id):
        created = create(client, url, owner)

        response = client.post(
            f"{url}/{created['id']}/prices",
            json={"resource_id": resource_id[BRICK], "unit_price": "230.00"},
            headers=owner,
        )

        assert response.json()["shipping_cost"] == "0.00"

    @pytest.mark.parametrize(
        "bad",
        [
            {"unit_price": "-1"},
            {"shipping_cost": "-0.01"},
            {"unit_price": "10.123"},
            {"unit_price": "abc"},
        ],
    )
    def test_malformed_amounts_are_422(self, client, url, owner, resource_id, bad):
        created = create(client, url, owner)

        response = add_price(client, url, owner, created["id"], resource_id, **bad)

        assert response.status_code == 422

    def test_labour_is_422(self, client, url, owner, resource_id):
        created = create(client, url, owner)

        response = add_price(client, url, owner, created["id"], resource_id, material=LABOR)

        assert response.status_code == 422

    def test_an_unknown_material_is_422(self, client, url, owner):
        created = create(client, url, owner)

        response = client.post(
            f"{url}/{created['id']}/prices",
            json={"resource_id": 999_999, "unit_price": "1.00"},
            headers=owner,
        )

        assert response.status_code == 422

    def test_a_material_already_in_the_list_is_409(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        add_price(client, url, owner, created["id"], resource_id)

        assert add_price(client, url, owner, created["id"], resource_id).status_code == 409

    def test_the_same_material_in_two_lists_is_fine(self, client, url, owner, resource_id):
        first = create(client, url, owner, name="Uno")
        second = create(client, url, owner, name="Dos")

        assert add_price(client, url, owner, first["id"], resource_id).status_code == 201
        assert add_price(client, url, owner, second["id"], resource_id).status_code == 201

    def test_the_list_is_by_material_name(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        add_price(client, url, owner, created["id"], resource_id, material=CEMENT)
        add_price(client, url, owner, created["id"], resource_id, material=BRICK)

        rows = client.get(f"{url}/{created['id']}/prices", headers=owner).json()

        assert [row["resource"]["name"] for row in rows] == [CEMENT, BRICK]

    def test_patch_changes_the_amounts_and_not_the_material(
        self, client, url, owner, resource_id
    ):
        created = create(client, url, owner)
        row = add_price(client, url, owner, created["id"], resource_id).json()

        response = client.patch(
            f"{url}/{created['id']}/prices/{row['id']}",
            json={"unit_price": "260.00"},
            headers=owner,
        )

        assert response.status_code == 200
        assert response.json()["unit_price"] == "260.00"
        assert response.json()["shipping_cost"] == "1500.00"
        assert response.json()["resource"]["id"] == resource_id[BRICK]

    def test_patch_with_a_negative_amount_is_422(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        row = add_price(client, url, owner, created["id"], resource_id).json()

        response = client.patch(
            f"{url}/{created['id']}/prices/{row['id']}", json={"shipping_cost": "-1"}, headers=owner
        )

        assert response.status_code == 422

    def test_deactivate_a_row_answers_204_and_the_list_loses_it(
        self, client, url, owner, resource_id
    ):
        created = create(client, url, owner)
        row = add_price(client, url, owner, created["id"], resource_id).json()

        response = client.post(
            f"{url}/{created['id']}/prices/{row['id']}/deactivate", headers=owner
        )

        assert response.status_code == 204
        assert client.get(f"{url}/{created['id']}/prices", headers=owner).json() == []
        assert client.get(f"{url}/{created['id']}", headers=owner).json()["price_count"] == 0

    def test_a_row_is_404_through_another_supplier_s_id(self, client, url, owner, resource_id):
        mine = create(client, url, owner, name="Uno")
        other = create(client, url, owner, name="Dos")
        row = add_price(client, url, owner, mine["id"], resource_id).json()

        target = f"{url}/{other['id']}/prices/{row['id']}"

        assert client.patch(target, json={"unit_price": "1.00"}, headers=owner).status_code == 404
        assert client.post(f"{target}/deactivate", headers=owner).status_code == 404

    def test_nothing_is_added_to_a_deactivated_supplier(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        client.post(f"{url}/{created['id']}/deactivate", headers=owner)

        assert add_price(client, url, owner, created["id"], resource_id).status_code == 404

    def test_nothing_is_added_to_another_firm_s_supplier(
        self, client, world, url, owner, stranger, resource_id
    ):
        theirs = create(client, f"/firms/{world.firm_b}/suppliers", stranger)

        assert add_price(client, url, owner, theirs["id"], resource_id).status_code == 404

    def test_there_is_no_way_to_delete_a_row(self, client, url, owner, resource_id):
        created = create(client, url, owner)
        row = add_price(client, url, owner, created["id"], resource_id).json()

        response = client.delete(f"{url}/{created['id']}/prices/{row['id']}", headers=owner)

        assert response.status_code == 405
