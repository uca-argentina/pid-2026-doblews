"""/firms/{firm_id}/members: the roster endpoints of HU-2.

The route audit in test_route_permissions.py already proves every one of these
declares a permission, resolves the roster, and answers an outsider with 404.
This file is about what each endpoint does for the people allowed in, and about
who is not.
"""

from datetime import datetime

import pytest

from app.services.roster import ALREADY_MEMBER


def members_url(firm_id: int) -> str:
    return f"/firms/{firm_id}/members"


class TestListMembers:
    def test_the_owner_sees_the_roster_with_labels_and_state(self, client, world, auth_header):
        response = client.get(members_url(world.firm_a), headers=auth_header(world.account_a))

        assert response.status_code == 200
        body = response.json()
        # joined_at is set by the database, so it is checked for shape only.
        for member in body:
            datetime.fromisoformat(member.pop("joined_at"))
        assert body == [
            {
                "account_id": world.account_a2,
                "name": "alba",
                "email": "alba@test.com",
                "role": {"code": "architect", "name": "Arquitecto"},
                "is_active": True,
            },
            {
                "account_id": world.account_a,
                "name": "ana",
                "email": "ana@test.com",
                "role": {"code": "owner", "name": "Propietario"},
                "is_active": True,
            },
        ]

    def test_people_who_left_are_listed_as_inactive(self, client, world, auth_header, new_member):
        """HU-2's listing shows state, and the listing is where the owner finds
        someone to bring back."""
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        body = client.get(members_url(world.firm_a), headers=auth_header(world.account_a)).json()

        assert {member["account_id"]: member["is_active"] for member in body}[gone] is False

    def test_an_architect_can_read_it(self, client, world, auth_header):
        """member.view: HU-3's client picker is filled from here, and architects
        create projects."""
        response = client.get(members_url(world.firm_a), headers=auth_header(world.account_a2))

        assert response.status_code == 200

    def test_a_firm_client_cannot(self, client, world, auth_header, new_member):
        """On the roster, so the firm exists for them: 403, not 404."""
        firm_client = new_member(world.firm_a, "cliente@test.com", "client")

        response = client.get(members_url(world.firm_a), headers=auth_header(firm_client))

        assert response.status_code == 403

    def test_someone_who_left_cannot_read_it_either(self, client, world, auth_header, new_member):
        """Leaving the roster closes this firm's door: 404, like any outsider."""
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        response = client.get(members_url(world.firm_a), headers=auth_header(gone))

        assert response.status_code == 404

    def test_anonymous_gets_401(self, client, world):
        assert client.get(members_url(world.firm_a)).status_code == 401


class TestListMemberRoles:
    def test_offers_architect_and_client_with_their_seeded_labels(self, client, world, auth_header):
        response = client.get(
            f"{members_url(world.firm_a)}/roles", headers=auth_header(world.account_a)
        )

        assert response.status_code == 200
        assert response.json() == [
            {"code": "architect", "name": "Arquitecto"},
            {"code": "client", "name": "Cliente"},
        ]

    def test_an_architect_cannot_see_them(self, client, world, auth_header):
        """member.add: an architect cannot add anyone, so has no form to fill."""
        response = client.get(
            f"{members_url(world.firm_a)}/roles", headers=auth_header(world.account_a2)
        )

        assert response.status_code == 403


def new_person(**overrides) -> dict:
    return {
        "name": "Nueva Persona",
        "email": "nueva@test.com",
        "role_code": "architect",
        "password": "clave-inicial",
    } | overrides


class TestAddMember:
    def test_a_new_address_joins_the_roster(self, client, world, auth_header):
        response = client.post(
            members_url(world.firm_a), json=new_person(), headers=auth_header(world.account_a)
        )

        assert response.status_code == 201
        body = response.json()
        assert (body["name"], body["email"], body["role"], body["is_active"]) == (
            "Nueva Persona",
            "nueva@test.com",
            {"code": "architect", "name": "Arquitecto"},
            True,
        )

    def test_the_new_account_logs_in_with_the_typed_password(self, client, world, auth_header):
        client.post(
            members_url(world.firm_a), json=new_person(), headers=auth_header(world.account_a)
        )

        login = client.post(
            "/auth/login", json={"email": "nueva@test.com", "password": "clave-inicial"}
        )

        assert login.status_code == 200

    def test_an_existing_account_gets_the_same_answer(self, client, world, auth_header):
        """HU-2: the add never reveals whether the address already had an account."""
        headers = auth_header(world.account_a)

        new = client.post(members_url(world.firm_a), json=new_person(), headers=headers)
        existing = client.post(
            members_url(world.firm_a), json=new_person(email="bruno@test.com"), headers=headers
        )

        assert new.status_code == existing.status_code == 201
        assert new.json().keys() == existing.json().keys()

    def test_an_existing_account_keeps_its_name_and_password(
        self, client, world, auth_header, usable_passwords
    ):
        response = client.post(
            members_url(world.firm_a),
            json=new_person(email="bruno@test.com", name="Otro Nombre"),
            headers=auth_header(world.account_a),
        )

        def login(password: str) -> int:
            credentials = {"email": "bruno@test.com", "password": password}
            return client.post("/auth/login", json=credentials).status_code

        assert response.json()["name"] == "bruno"
        assert login(usable_passwords) == 200
        assert login("clave-inicial") == 401

    def test_the_address_is_stored_trimmed_and_lowercased(self, client, world, auth_header):
        response = client.post(
            members_url(world.firm_a),
            json=new_person(email="  Nueva@Test.COM "),
            headers=auth_header(world.account_a),
        )

        assert response.json()["email"] == "nueva@test.com"

    def test_the_seeds_test_domain_is_accepted(self, client, world, auth_header):
        """.test is a special-use name that plain EmailStr refuses, and the
        development seed lives there: the demo adds bruno@estudiosur.test."""
        response = client.post(
            members_url(world.firm_a),
            json=new_person(email="bruno@estudiosur.test"),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 201

    @pytest.mark.parametrize(
        "overrides",
        [
            {"email": "sin-arroba"},
            {"role_code": "owner"},
            {"name": "   "},
            {"password": "corta"},
            # 40 characters, 80 bytes: past bcrypt's limit although short to the eye.
            {"password": "ñ" * 40},
        ],
        ids=["bad email", "owner role", "blank name", "short password", "password over 72 bytes"],
    )
    def test_invalid_input_is_a_422(self, client, world, auth_header, overrides):
        response = client.post(
            members_url(world.firm_a),
            json=new_person(**overrides),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422

    def test_an_active_member_is_a_409(self, client, world, auth_header):
        response = client.post(
            members_url(world.firm_a),
            json=new_person(email="alba@test.com"),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": ALREADY_MEMBER}

    def test_someone_who_left_comes_back(self, client, world, auth_header, new_member):
        gone = new_member(world.firm_a, "carla@test.com", "architect", is_active=False)

        response = client.post(
            members_url(world.firm_a),
            json=new_person(email="carla@test.com", role_code="client"),
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 201
        body = response.json()
        assert (body["account_id"], body["role"]["code"], body["is_active"]) == (
            gone,
            "client",
            True,
        )

    def test_an_architect_cannot_add_anyone(self, client, world, auth_header):
        response = client.post(
            members_url(world.firm_a), json=new_person(), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 403

    def test_another_firms_owner_gets_404(self, client, world, auth_header):
        """The route audit only exercises GETs, so the write routes prove it here."""
        response = client.post(
            members_url(world.firm_a), json=new_person(), headers=auth_header(world.account_b)
        )

        assert response.status_code == 404
