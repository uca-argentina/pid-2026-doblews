"""/firms/{firm_id}/members: the roster endpoints of HU-2.

The route audit in test_route_permissions.py already proves every one of these
declares a permission, resolves the roster, and answers an outsider with 404.
This file is about what each endpoint does for the people allowed in, and about
who is not.
"""

from datetime import datetime

import pytest
from sqlalchemy import text

from app.api.routes.members import MEMBER_NOT_FOUND
from app.services.authz import project_permissions
from app.services.roster import (
    ALREADY_MEMBER,
    CANNOT_CHANGE_OWN_ROLE,
    CANNOT_REMOVE_YOURSELF,
    CLIENT_WITH_PROJECT_ROLES,
    LEADS_ACTIVE_PROJECTS,
)


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


class TestChangeRole:
    def url(self, world, account_id: int) -> str:
        return f"{members_url(world.firm_a)}/{account_id}"

    def test_the_owner_changes_a_members_role(self, client, world, auth_header):
        response = client.patch(
            self.url(world, world.account_a2),
            json={"role_code": "client"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200
        assert response.json()["role"] == {"code": "client", "name": "Cliente"}

    def test_the_email_is_not_editable(self, client, world, auth_header):
        """HU-2: the email is a global identity. Sent anyway, it is not read."""
        response = client.patch(
            self.url(world, world.account_a2),
            json={"role_code": "client", "email": "otra@test.com", "name": "Otra"},
            headers=auth_header(world.account_a),
        )

        assert (response.json()["email"], response.json()["name"]) == ("alba@test.com", "alba")

    def test_the_owner_cannot_change_their_own_role(self, client, world, auth_header):
        response = client.patch(
            self.url(world, world.account_a),
            json={"role_code": "architect"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": CANNOT_CHANGE_OWN_ROLE}

    def test_a_lead_cannot_become_a_client(self, client, world, auth_header, add_project_member):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")

        response = client.patch(
            self.url(world, world.account_a2),
            json={"role_code": "client"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 409
        assert response.json() == {"detail": CLIENT_WITH_PROJECT_ROLES}

    def test_owner_is_not_a_role_that_can_be_given(self, client, world, auth_header):
        response = client.patch(
            self.url(world, world.account_a2),
            json={"role_code": "owner"},
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 422

    def test_a_member_of_another_firm_is_not_found(self, client, world, auth_header):
        """Bruno exists, but not in firm_a: the same 404 as an id that does not."""
        headers = auth_header(world.account_a)

        someone_elses = client.patch(
            self.url(world, world.account_b), json={"role_code": "client"}, headers=headers
        )
        nonexistent = client.patch(
            self.url(world, 999999), json={"role_code": "client"}, headers=headers
        )

        assert someone_elses.status_code == nonexistent.status_code == 404
        assert someone_elses.json() == nonexistent.json() == {"detail": MEMBER_NOT_FOUND}

    def test_an_architect_cannot_change_roles(self, client, world, auth_header, new_member):
        firm_client = new_member(world.firm_a, "cliente@test.com", "client")

        response = client.patch(
            self.url(world, firm_client),
            json={"role_code": "architect"},
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403


class TestRemoveMember:
    def url(self, world, account_id: int) -> str:
        return f"{members_url(world.firm_a)}/{account_id}"

    def test_the_owner_removes_a_member(self, client, world, auth_header):
        headers = auth_header(world.account_a)

        response = client.delete(self.url(world, world.account_a2), headers=headers)

        assert response.status_code == 204
        assert response.content == b""
        roster = client.get(members_url(world.firm_a), headers=headers).json()
        assert {member["account_id"]: member["is_active"] for member in roster} == {
            world.account_a: True,
            world.account_a2: False,
        }

    def test_the_removed_person_keeps_working_elsewhere(
        self, client, world, auth_header, join_roster, usable_passwords
    ):
        """HU-2: "la persona deja de ver este estudio, pero sigue pudiendo
        loguearse y trabajar en otros"."""
        join_roster(world.firm_b, world.account_a2, "architect")

        client.delete(self.url(world, world.account_a2), headers=auth_header(world.account_a))

        alba = auth_header(world.account_a2)
        credentials = {"email": "alba@test.com", "password": usable_passwords}
        assert client.post("/auth/login", json=credentials).status_code == 200
        assert client.get(f"/firms/{world.firm_a}", headers=alba).status_code == 404
        assert client.get(f"/firms/{world.firm_b}", headers=alba).status_code == 200
        me = client.get("/auth/me", headers=alba).json()
        assert [firm["id"] for firm in me["firms"]] == [world.firm_b]

    def test_removing_and_adding_back_restores_her_projects(
        self, client, db, db_session, world, auth_header, add_project_member
    ):
        """The full cycle HU-2 promises: "si la reincorporo, vuelven solas"."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "collaborator")
        headers = auth_header(world.account_a)

        def alba_on_project_a() -> frozenset[str]:
            return project_permissions(db_session, world.account_a2, world.project_a, world.firm_a)

        client.delete(self.url(world, world.account_a2), headers=headers)
        assert alba_on_project_a() == frozenset()

        client.post(
            members_url(world.firm_a),
            json=new_person(email="alba@test.com"),
            headers=headers,
        )
        assert "project.edit" in alba_on_project_a()

        rows = db.execute(
            text("SELECT count(*) FROM project_member WHERE account_id = :a"),
            {"a": world.account_a2},
        ).scalar_one()
        assert rows == 1, "nothing was reassigned: the same row came back to life"

    def test_the_owner_cannot_remove_themselves(self, client, world, auth_header):
        response = client.delete(
            self.url(world, world.account_a), headers=auth_header(world.account_a)
        )

        assert response.status_code == 409
        assert response.json() == {"detail": CANNOT_REMOVE_YOURSELF}

    def test_the_lead_of_a_live_project_cannot_be_removed(
        self, client, world, auth_header, add_project_member
    ):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "lead")

        response = client.delete(
            self.url(world, world.account_a2), headers=auth_header(world.account_a)
        )

        assert response.status_code == 409
        assert response.json() == {"detail": LEADS_ACTIVE_PROJECTS}

    def test_removing_twice_is_not_found(self, client, world, auth_header):
        headers = auth_header(world.account_a)
        client.delete(self.url(world, world.account_a2), headers=headers)

        response = client.delete(self.url(world, world.account_a2), headers=headers)

        assert response.status_code == 404
        assert response.json() == {"detail": MEMBER_NOT_FOUND}

    def test_a_member_of_another_firm_is_not_found(self, client, world, auth_header):
        response = client.delete(
            self.url(world, world.account_b), headers=auth_header(world.account_a)
        )

        assert response.status_code == 404

    def test_an_architect_cannot_remove_anyone(self, client, world, auth_header, new_member):
        firm_client = new_member(world.firm_a, "cliente@test.com", "client")

        response = client.delete(
            self.url(world, firm_client), headers=auth_header(world.account_a2)
        )

        assert response.status_code == 403

    def test_another_firms_owner_gets_404(self, client, world, auth_header):
        response = client.delete(
            self.url(world, world.account_a2), headers=auth_header(world.account_b)
        )

        assert response.status_code == 404
