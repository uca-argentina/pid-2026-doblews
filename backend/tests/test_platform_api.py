"""/platform: the support endpoints of HU-7.

The route audit in test_route_permissions.py already proves every one of these
demands a platform permission, resolves no roster, and refuses an owner. This
file is about what each endpoint does for support, and about who is not support.
The rules themselves are pinned in test_platform_service.py; here they are only
followed as far as the status code and the shape.
"""

from datetime import datetime

import pytest
from sqlalchemy import text

from app.api.routes.platform import ACCOUNT_NOT_FOUND, FIRM_NOT_FOUND
from app.services.platform import STAFF_CANNOT_OWN

FIRMS_URL = "/platform/firms"
RESET_URL = "/platform/accounts/password"


def firm_body(owner_email: str = "duena@oeste.test", **overrides) -> dict:
    body = {
        "name": "Oeste",
        "contact_email": "Contacto@Oeste.test",
        "phone": "351 555-0000",
        "owner": {"name": "Nueva Dueña", "email": owner_email, "password": "clave-inicial"},
    }
    body.update(overrides)
    return body


def login(client, email: str, password: str):
    return client.post("/auth/login", json={"email": email, "password": password})


@pytest.fixture
def support(support_account, auth_header) -> dict[str, str]:
    return auth_header(support_account)


class TestWhoGetsIn:
    def test_anonymous_gets_401(self, client):
        assert client.get(FIRMS_URL).status_code == 401

    @pytest.mark.parametrize(
        ("method", "url", "body"),
        [
            ("post", FIRMS_URL, firm_body()),
            ("patch", f"{FIRMS_URL}/1", {"is_active": False}),
            ("put", RESET_URL, {"email": "ana@test.com", "password": "clave-nueva"}),
        ],
        ids=["create", "suspend", "reset"],
    )
    def test_an_owner_cannot_write(self, client, world, auth_header, method, url, body):
        """The GETs are covered by the route audit; writes need a valid body to
        reach the permission check, so they are exercised here."""
        response = getattr(client, method)(url, json=body, headers=auth_header(world.account_a))

        assert response.status_code == 403


class TestListFirms:
    def test_support_sees_every_firm_with_its_head_count(self, client, world, support):
        response = client.get(FIRMS_URL, headers=support)

        assert response.status_code == 200
        body = response.json()
        for firm in body:
            datetime.fromisoformat(firm.pop("created_at"))
        assert body == [
            {
                "id": world.firm_a,
                "name": "norte",
                "contact_email": "norte@test.com",
                "phone": None,
                "is_active": True,
                "member_count": 2,
            },
            {
                "id": world.firm_b,
                "name": "sur",
                "contact_email": "sur@test.com",
                "phone": None,
                "is_active": True,
                "member_count": 1,
            },
        ]


class TestCreateFirm:
    def test_creates_the_firm_and_its_owner_can_log_in_to_it(self, client, world, support):
        response = client.post(FIRMS_URL, json=firm_body(), headers=support)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Oeste"
        # Normalized the way account stores it, and the same for the firm.
        assert body["contact_email"] == "contacto@oeste.test"
        assert (body["is_active"], body["member_count"]) == (True, 1)
        assert body["owner"]["name"] == "Nueva Dueña"
        assert body["owner"]["email"] == "duena@oeste.test"
        assert body["owner"]["account_existed"] is False

        token = login(client, "duena@oeste.test", "clave-inicial").json()["access_token"]
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
        assert [(firm["id"], firm["role"]["code"]) for firm in me["firms"]] == [
            (body["id"], "owner")
        ]

    def test_an_existing_account_is_returned_as_such_with_its_own_name(
        self, client, world, support
    ):
        """What lets the UI tell support the typed name and password were not used."""
        response = client.post(FIRMS_URL, json=firm_body("bruno@test.com"), headers=support)

        assert response.status_code == 201
        assert response.json()["owner"] == {
            "account_id": world.account_b,
            "name": "bruno",
            "email": "bruno@test.com",
            "account_existed": True,
        }

    def test_a_blank_phone_is_stored_as_none(self, client, world, support):
        response = client.post(FIRMS_URL, json=firm_body(phone="   "), headers=support)

        assert response.json()["phone"] is None

    def test_a_staff_owner_is_a_409_with_the_reason(self, client, support):
        response = client.post(FIRMS_URL, json=firm_body("soporte@test.com"), headers=support)

        assert response.status_code == 409
        assert response.json()["detail"] == STAFF_CANNOT_OWN

    @pytest.mark.parametrize(
        "overrides",
        [
            {"name": "   "},
            {"contact_email": "no-es-un-email"},
            {"phone": "1" * 31},
            {"owner": {"name": "X", "email": "x@oeste.test", "password": "corta"}},
            {"owner": {"name": "X", "email": "x@oeste.test", "password": "ñ" * 40}},
        ],
        ids=["blank-name", "bad-email", "long-phone", "short-password", "password-over-72-bytes"],
    )
    def test_an_invalid_body_is_a_422_and_writes_nothing(self, client, world, support, overrides):
        response = client.post(FIRMS_URL, json=firm_body(**overrides), headers=support)

        assert response.status_code == 422
        assert len(client.get(FIRMS_URL, headers=support).json()) == 2


class TestChangeFirmStatus:
    def test_suspending_locks_the_owner_out_and_reactivating_lets_them_back(
        self, client, world, support, auth_header
    ):
        owner = auth_header(world.account_a)
        url = f"{FIRMS_URL}/{world.firm_a}"

        suspended = client.patch(url, json={"is_active": False}, headers=support)

        assert suspended.status_code == 200
        assert suspended.json()["is_active"] is False
        assert client.get(f"/firms/{world.firm_a}", headers=owner).status_code == 404

        reactivated = client.patch(url, json={"is_active": True}, headers=support)

        assert reactivated.json()["is_active"] is True
        assert client.get(f"/firms/{world.firm_a}", headers=owner).status_code == 200

    def test_an_unknown_firm_is_a_404(self, client, support):
        response = client.patch(f"{FIRMS_URL}/999999", json={"is_active": False}, headers=support)

        assert response.status_code == 404
        assert response.json()["detail"] == FIRM_NOT_FOUND


class TestResetPassword:
    def test_the_new_password_works_and_the_old_one_does_not(
        self, client, world, support, usable_passwords
    ):
        response = client.put(
            RESET_URL, json={"email": "Ana@Test.com", "password": "clave-nueva"}, headers=support
        )

        assert response.status_code == 204
        assert login(client, "ana@test.com", "clave-nueva").status_code == 200
        assert login(client, "ana@test.com", usable_passwords).status_code == 401

    @pytest.mark.parametrize(
        "email", ["nadie@test.com", "soporte@test.com"], ids=["unknown", "staff"]
    )
    def test_an_account_support_cannot_reset_is_a_404(self, client, support, email):
        response = client.put(
            RESET_URL, json={"email": email, "password": "clave-nueva"}, headers=support
        )

        assert response.status_code == 404
        assert response.json()["detail"] == ACCOUNT_NOT_FOUND

    def test_a_short_password_is_a_422(self, client, world, support):
        response = client.put(
            RESET_URL, json={"email": "ana@test.com", "password": "corta"}, headers=support
        )

        assert response.status_code == 422


def test_support_still_sees_no_firm_content(client, world, support):
    """ADR-002 section 7, from the outside: platform permissions open no firm."""
    assert client.get(f"/firms/{world.firm_a}", headers=support).status_code == 404
    assert client.get(f"/firms/{world.firm_a}/projects", headers=support).status_code == 404


def test_nothing_is_left_half_written_when_a_firm_is_refused(client, db, support):
    """ADR-002 section 10 from the outside: a refused create leaves no firm."""
    before = db.execute(text("SELECT count(*) FROM firm")).scalar_one()

    client.post(FIRMS_URL, json=firm_body("soporte@test.com"), headers=support)

    assert db.execute(text("SELECT count(*) FROM firm")).scalar_one() == before
