"""Resolving permissions from the seeded catalogue, with no HTTP involved.

Two things are under test. That a role grants exactly what ADR-002 section 7
wired to it, and that a project assignment grants nothing once the firm door
behind it is closed.
"""

from sqlalchemy import text

from app.services.auth import get_firm_membership
from app.services.authz import firm_permissions, platform_permissions, project_permissions


def firm_permissions_of(db_session, account_id: int, firm_id: int) -> frozenset[str]:
    """Go through the roster row, the way a request does."""
    membership = get_firm_membership(db_session, account_id=account_id, firm_id=firm_id)
    assert membership is not None
    return firm_permissions(db_session, membership.role_id)


class TestFirmScope:
    def test_owner_manages_the_roster_and_sees_every_project(self, db_session, world):
        granted = firm_permissions_of(db_session, world.account_a, world.firm_a)

        assert {"member.add", "member.edit_role", "member.remove"} <= granted
        # A firm-scope permission that changes which project rows a read returns.
        assert "project.view_all" in granted

    def test_architect_reads_the_roster_but_cannot_change_it(self, db_session, world):
        granted = firm_permissions_of(db_session, world.account_a2, world.firm_a)

        assert "member.view" in granted
        assert "member.add" not in granted
        assert "project.create" in granted
        assert "project.view_all" not in granted

    def test_no_firm_role_grants_project_scope_permissions(self, db_session, world):
        """project.view lives in project scope. Reading it out of a firm role
        would mean the scope filter is not doing its job."""
        granted = firm_permissions_of(db_session, world.account_a, world.firm_a)

        assert "project.view" not in granted
        assert "project.edit" not in granted


class TestPlatformScope:
    def test_an_ordinary_account_has_no_platform_permissions(self, db_session, world):
        assert platform_permissions(db_session, world.account_a) == frozenset()

    def test_support_administers_accounts_and_never_content(self, db_session, role_id):
        """ADR-002 section 7: the support role must not hold a single project.*
        permission, so that a bug in permission resolution can never become a
        leak between competing firms."""
        account_id = db_session.execute(
            text(
                "INSERT INTO account (name, email, password_hash)"
                " VALUES ('Soporte', 'soporte@test.com', 'x') RETURNING id"
            )
        ).scalar_one()
        db_session.execute(
            text(
                "INSERT INTO platform_member (account_id, role_id, role_scope)"
                " VALUES (:a, :r, 'platform')"
            ),
            {"a": account_id, "r": role_id[("support", "platform")]},
        )

        granted = platform_permissions(db_session, account_id)

        assert {"firm.create", "firm.suspend", "account.reset_password"} <= granted
        assert not any(code.startswith("project.") for code in granted)


class TestProjectScope:
    def test_lead_edits_the_project_and_manages_its_team(
        self, db_session, world, add_project_member
    ):
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")

        granted = project_permissions(
            db_session,
            account_id=world.account_a,
            project_id=world.project_a,
            firm_id=world.firm_a,
        )

        assert {"project.view", "project.edit", "project.member.manage"} <= granted

    def test_viewer_reads_without_editing(self, db_session, world, add_project_member):
        add_project_member(world.project_a, world.account_a2, world.firm_a, "viewer")

        granted = project_permissions(
            db_session,
            account_id=world.account_a2,
            project_id=world.project_a,
            firm_id=world.firm_a,
        )

        assert "project.view" in granted
        assert "project.edit" not in granted
        assert "project.member.manage" not in granted

    def test_someone_with_no_assignment_gets_nothing(self, db_session, world):
        assert (
            project_permissions(
                db_session,
                account_id=world.account_a2,
                project_id=world.project_a,
                firm_id=world.firm_a,
            )
            == frozenset()
        )

    def test_leaving_the_roster_makes_project_rows_inert(
        self, db_session, world, add_project_member
    ):
        """ADR-002 section 11.3. The project_member row is deliberately not
        deleted, so the assignments come back on their own if the person is
        reinstated. Until then it must grant nothing."""
        add_project_member(world.project_a, world.account_a, world.firm_a, "lead")
        db_session.execute(
            text("UPDATE firm_member SET is_active = false WHERE account_id = :a"),
            {"a": world.account_a},
        )

        granted = project_permissions(
            db_session,
            account_id=world.account_a,
            project_id=world.project_a,
            firm_id=world.firm_a,
        )

        assert granted == frozenset()
        # The row is still there: inert, not gone.
        assert (
            db_session.execute(
                text("SELECT count(*) FROM project_member WHERE account_id = :a"),
                {"a": world.account_a},
            ).scalar_one()
            == 1
        )

    def test_asking_under_the_wrong_firm_grants_nothing(
        self, db_session, world, add_project_member
    ):
        """Bruno's own project, asked for as if it belonged to Ana's firm."""
        add_project_member(world.project_b, world.account_b, world.firm_b, "lead")

        granted = project_permissions(
            db_session,
            account_id=world.account_b,
            project_id=world.project_b,
            firm_id=world.firm_a,
        )

        assert granted == frozenset()
