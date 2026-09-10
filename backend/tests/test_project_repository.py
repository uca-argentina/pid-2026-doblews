"""Which project rows a read returns — the second level of enforcement.

ADR-002 section 8: "Un permiso no salva de un WHERE olvidado." These tests are
about the WHERE, so most of them pass the permission set in by hand rather than
resolving it: what is under test is the query, not the catalogue.
"""

import pytest
from sqlalchemy import text

from app.repositories.base import FirmScopedRepository
from app.repositories.project import VIEW_ALL, ProjectRepository
from app.services.auth import get_firm_membership
from app.services.authz import firm_permissions

MEMBER_ONLY = frozenset()
SEES_EVERYTHING = frozenset({VIEW_ALL})


@pytest.fixture
def new_project(db):
    """Another project, so "all of them" and "in name order" have something to say."""

    def _new(firm_id: int, created_by: int, name: str, is_active: bool = True) -> int:
        return db.execute(
            text(
                "INSERT INTO project (firm_id, name, created_by, is_active)"
                " VALUES (:f, :n, :c, :a) RETURNING id"
            ),
            {"f": firm_id, "n": name, "c": created_by, "a": is_active},
        ).scalar_one()

    return _new


def repo(db_session, firm_id: int) -> ProjectRepository:
    return ProjectRepository(db_session, firm_id=firm_id)


class TestMembership:
    def test_a_member_sees_the_project_they_are_on(self, db_session, world, add_project_member):
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")

        found = repo(db_session, world.firm_a).list_visible(world.account_a, MEMBER_ONLY)

        assert [project.id for project in found] == [world.project_a]

    def test_belonging_to_the_firm_is_not_belonging_to_its_projects(self, db_session, world):
        """Ana is on firm_a's roster and on no project of it. HU-3: "solo veo las
        obras del estudio activo donde soy miembro"."""
        found = repo(db_session, world.firm_a).list_visible(world.account_a, MEMBER_ONLY)

        assert found == []

    def test_projects_come_back_in_name_order(
        self, db_session, world, new_project, add_project_member
    ):
        for name in ("Zulema", "Alfa"):
            project_id = new_project(world.firm_a, world.account_a, name)
            add_project_member(project_id, world.account_a, world.firm_a, "collaborator")

        found = repo(db_session, world.firm_a).list_visible(world.account_a, MEMBER_ONLY)

        assert [project.name for project in found] == ["Alfa", "Zulema"]


class TestViewAll:
    def test_view_all_returns_projects_the_caller_is_not_on(self, db_session, world, new_project):
        """The permission is firm-scope, and it changes which project rows come
        back. That is why an endpoint guard cannot do this job."""
        other = new_project(world.firm_a, world.account_a, "Casa ajena")

        found = repo(db_session, world.firm_a).list_visible(world.account_a, SEES_EVERYTHING)

        assert {project.id for project in found} == {world.project_a, other}

    def test_view_all_still_stops_at_the_firm_boundary(self, db_session, world):
        """The strongest project permission in the catalogue, and it still does
        not reach across tenants: that is section 8's whole point."""
        found = repo(db_session, world.firm_a).list_visible(world.account_a, SEES_EVERYTHING)

        assert world.project_b not in {project.id for project in found}

    def test_the_owner_really_holds_it(self, db_session, world, new_project):
        """The one case that goes through the catalogue instead of a literal set,
        so the seed and this query are shown to agree."""
        membership = get_firm_membership(
            db_session, account_id=world.account_a, firm_id=world.firm_a
        )
        assert membership is not None
        granted = firm_permissions(db_session, membership.role_id)
        other = new_project(world.firm_a, world.account_a, "Casa ajena")

        found = repo(db_session, world.firm_a).list_visible(world.account_a, granted)

        assert {project.id for project in found} == {world.project_a, other}

    def test_the_architect_does_not(self, db_session, world):
        membership = get_firm_membership(
            db_session, account_id=world.account_a2, firm_id=world.firm_a
        )
        assert membership is not None
        granted = firm_permissions(db_session, membership.role_id)

        found = repo(db_session, world.firm_a).list_visible(world.account_a2, granted)

        assert found == []


class TestArchived:
    def test_an_archived_project_is_gone_even_for_view_all(self, db_session, world, new_project):
        """Logical deletion, filtered in the base select so no caller can forget."""
        new_project(world.firm_a, world.account_a, "Obra vieja", is_active=False)

        found = repo(db_session, world.firm_a).list_visible(world.account_a, SEES_EVERYTHING)

        assert [project.id for project in found] == [world.project_a]


class TestGetVisible:
    def test_returns_a_project_the_caller_may_see(self, db_session, world, add_project_member):
        add_project_member(world.project_a, world.account_a, world.firm_a, "viewer")

        found = repo(db_session, world.firm_a).get_visible(
            world.project_a, world.account_a, MEMBER_ONLY
        )

        assert found is not None and found.id == world.project_a

    def test_another_firms_project_is_none(self, db_session, world):
        """Asked for through firm_a, which is the only firm this caller proved."""
        assert (
            repo(db_session, world.firm_a).get_visible(
                world.project_b, world.account_a, SEES_EVERYTHING
            )
            is None
        )

    def test_a_project_of_this_firm_the_caller_is_not_on_is_none(self, db_session, world):
        assert (
            repo(db_session, world.firm_a).get_visible(
                world.project_a, world.account_a, MEMBER_ONLY
            )
            is None
        )

    def test_a_project_that_does_not_exist_is_none(self, db_session, world):
        """Same None as the two above, so the endpoint answers all of them with
        the same 404 and never confirms which case it was."""
        assert (
            repo(db_session, world.firm_a).get_visible(999999, world.account_a, SEES_EVERYTHING)
            is None
        )


def test_a_repository_cannot_scope_a_table_without_a_tenant():
    """account has no firm_id on purpose: it is the global identity, so one
    person can belong to several firms. Scoping it would be meaningless, and the
    class refuses to be defined rather than silently returning everything."""
    from app.models import Account

    with pytest.raises(TypeError, match="no firm_id"):

        class Accounts(FirmScopedRepository[Account]):
            model = Account
