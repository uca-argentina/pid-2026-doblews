"""The requires() dependency: the door that turns a missing permission into 403.

Tested against a throwaway app rather than the real one, so that what is proved
here is the dependency itself and not any one endpoint: one route per scope,
each demanding a permission one role holds and another lacks.

It was also the only way to prove it when T-03 wrote it, since no production
route could answer 403 yet. They can now: HU-2's roster writes refuse an
architect, and test_members_api.py covers those through the real routes.
"""

import inspect
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection
from sqlalchemy.orm import Session

from app.api.deps import FORBIDDEN, REQUIRED_PERMISSION, requires, requires_any
from app.db.session import get_db


@pytest.fixture
def guarded_client(db: Connection) -> Iterator[TestClient]:
    """An app with one route per scope, each demanding a permission.

    member.add is held by owner and not by architect; project.edit by lead and
    not by viewer. Both pairs come straight from the table in ADR-002 section 7.

    The third route is the OR: the same shape HU-3's project detail has, where a
    project permission and a firm one each open it on their own.
    """
    guarded = FastAPI()

    @guarded.get(
        "/firms/{firm_id}/roster",
        dependencies=[Depends(requires("member.add", "firm"))],
    )
    def manage_roster() -> dict[str, bool]:
        return {"reached": True}

    @guarded.get(
        "/firms/{firm_id}/projects/{project_id}",
        dependencies=[Depends(requires("project.edit", "project"))],
    )
    def edit_project() -> dict[str, bool]:
        return {"reached": True}

    @guarded.get(
        "/firms/{firm_id}/projects/{project_id}/detail",
        dependencies=[
            Depends(
                requires_any(
                    ("project.view", "project"),
                    ("project.view_all", "firm"),
                )
            )
        ],
    )
    def read_project() -> dict[str, bool]:
        return {"reached": True}

    def override_get_db() -> Iterator[Session]:
        session = Session(bind=db, autoflush=False, expire_on_commit=False)
        try:
            yield session
        finally:
            session.close()

    guarded.dependency_overrides[get_db] = override_get_db
    with TestClient(guarded) as test_client:
        yield test_client


class TestFirmScope:
    def test_a_role_that_grants_the_permission_gets_through(
        self, guarded_client, world, auth_header
    ):
        response = guarded_client.get(
            f"/firms/{world.firm_a}/roster", headers=auth_header(world.account_a)
        )

        assert response.status_code == 200
        assert response.json() == {"reached": True}

    def test_a_member_without_the_permission_is_forbidden(self, guarded_client, world, auth_header):
        """The architect holds member.view but not member.add, so HU-2 asks for
        403 here: they already know the firm exists, hiding it protects nothing."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/roster", headers=auth_header(world.account_a2)
        )

        assert response.status_code == 403
        assert response.json()["detail"] == FORBIDDEN

    def test_someone_from_another_firm_is_not_found(self, guarded_client, world, auth_header):
        """404 and not 403, even though the missing permission would also apply:
        a 403 would confirm the firm exists (ADR-002 section 9)."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/roster", headers=auth_header(world.account_b)
        )

        assert response.status_code == 404

    def test_an_anonymous_caller_is_unauthorized_before_anything_else(self, guarded_client, world):
        response = guarded_client.get(f"/firms/{world.firm_a}/roster")

        assert response.status_code == 401

    def test_leaving_the_roster_is_a_404_and_not_a_403(
        self, guarded_client, db, world, auth_header
    ):
        from sqlalchemy import text

        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"),
            {"a": world.account_a},
        )

        response = guarded_client.get(
            f"/firms/{world.firm_a}/roster", headers=auth_header(world.account_a)
        )

        assert response.status_code == 404


class TestProjectScope:
    def test_the_lead_may_edit(self, guarded_client, world, add_project_member, auth_header):
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")

        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200

    def test_a_viewer_may_not(self, guarded_client, world, add_project_member, auth_header):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "viewer")

        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}",
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403

    def test_a_firm_member_with_no_seat_on_the_project_is_forbidden(
        self, guarded_client, world, auth_header
    ):
        """Belonging to the firm opens the door to the firm, not to every work
        inside it: HU-3 says each person sees only the projects they are on."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 403

    def test_a_project_of_another_firm_grants_nothing(
        self, guarded_client, world, add_project_member, auth_header
    ):
        """Bruno leads his own project, and asks for it through Ana's firm."""
        add_project_member(world.project_b, world.account_b, world.firm_b, "lead")

        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_b}",
            headers=auth_header(world.account_b),
        )

        # 404: Bruno is not on firm_a's roster, so he never reaches the project.
        assert response.status_code == 404


class TestEitherScope:
    """requires_any: the shape HU-3's project detail needs.

    Ana owns firm A, so she holds project.view_all there and no project role at
    all. Alba is an architect: she holds neither, and only gets in through a
    project_member row. One route, two ways in, and each is exercised alone.
    """

    def test_the_project_permission_alone_opens_it(
        self, guarded_client, world, add_project_member, auth_header
    ):
        """Alba is on the project as a viewer, and holds no firm-wide grant."""
        add_project_member(world.project_a, world.account_a2, world.firm_a, "viewer")

        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/detail",
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 200
        assert response.json() == {"reached": True}

    def test_the_firm_permission_alone_opens_it(self, guarded_client, world, auth_header):
        """Ana has no project_member row here, which is the whole point: without
        the OR she would get a 403 on her own firm's work (HU-3)."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/detail",
            headers=auth_header(world.account_a),
        )

        assert response.status_code == 200

    def test_neither_is_forbidden(self, guarded_client, world, auth_header):
        """Alba belongs to the firm and to nothing inside it."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/detail",
            headers=auth_header(world.account_a2),
        )

        assert response.status_code == 403
        assert response.json()["detail"] == FORBIDDEN

    def test_an_outsider_is_still_not_found(self, guarded_client, world, auth_header):
        """The OR is about permissions, not about the tenant: Bruno is refused
        by the roster before either branch is looked at."""
        response = guarded_client.get(
            f"/firms/{world.firm_a}/projects/{world.project_a}/detail",
            headers=auth_header(world.account_b),
        )

        assert response.status_code == 404

    def test_an_anonymous_caller_is_unauthorized_before_anything_else(self, guarded_client, world):
        response = guarded_client.get(f"/firms/{world.firm_a}/projects/{world.project_a}/detail")

        assert response.status_code == 401


class TestTheDeclaration:
    """What the guard carries for the route audit to read."""

    def test_one_permission_is_stamped_as_a_tuple_of_pairs(self):
        """The shape test_route_permissions walks. Uniform across both builders,
        so an auditor never has to tell a pair from a tuple of pairs."""
        guard = requires("member.add", "firm")

        assert getattr(guard, REQUIRED_PERMISSION) == (("member.add", "firm"),)

    def test_several_permissions_are_stamped_in_the_order_declared(self):
        guard = requires_any(("project.view", "project"), ("project.view_all", "firm"))

        assert getattr(guard, REQUIRED_PERMISSION) == (
            ("project.view", "project"),
            ("project.view_all", "firm"),
        )

    def test_one_query_per_scope_however_many_permissions(self):
        """Two permissions of the same scope resolve that scope once: FastAPI
        caches a dependency per request, and both pairs read the same set."""
        guard = requires_any(("project.view", "project"), ("project.edit", "project"))

        assert list(inspect.signature(guard).parameters) == ["project"]


def test_an_unknown_scope_fails_when_the_route_is_declared():
    """At import time, not on the first request that happens to reach it."""
    with pytest.raises(ValueError, match="unknown scope"):
        requires("member.add", "estudio")  # type: ignore[arg-type]


def test_an_unknown_scope_fails_the_same_way_among_several():
    with pytest.raises(ValueError, match="unknown scope"):
        requires_any(("project.view", "project"), ("member.add", "estudio"))  # type: ignore[arg-type]


def test_declaring_no_permission_at_all_is_refused():
    """An empty requires_any() would let everyone through while still looking
    guarded, and the route audit would count it as a declaration."""
    with pytest.raises(ValueError, match="at least one"):
        requires_any()
