"""The rules of creating and changing a work (HU-3).

Against the session directly, without HTTP: what is under test is the rule and
the transaction, not the status code it eventually becomes. The API tests cover
that half.

The two invariants that matter most here are the ones ADR-002 section 11 sends
to the service layer because the schema cannot hold them: a work is never
created without its lead, and the client of a work is a client of the firm.
"""

from datetime import date

import pytest
from sqlalchemy import text

from app.repositories.project import VIEW_ALL, ProjectRepository
from app.services.project import (
    CLIENT_IS_NOT_A_CLIENT,
    CLIENT_NOT_ON_ROSTER,
    FIRM_CLIENT_CANNOT_LEAD,
    ProjectError,
    archive_project,
    create_project,
    update_project,
)

SEES_EVERYTHING = frozenset({VIEW_ALL})


def team(db_session, project_id: int) -> dict[int, str]:
    """account_id -> role_code, read straight from the table."""
    rows = db_session.execute(
        text("SELECT account_id, role_code FROM project_member WHERE project_id = :p"),
        {"p": project_id},
    ).all()
    return {row.account_id: row.role_code for row in rows}


def entry(db_session, world, project_id: int):
    return ProjectRepository(db_session, firm_id=world.firm_a).entry(
        project_id, world.account_a, SEES_EVERYTHING
    )


class TestCreate:
    def test_the_creator_leads_the_work_it_created(self, db_session, world):
        """HU-3: without this the architect creates a work they cannot see."""
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        assert team(db_session, project.id) == {world.account_a2: "lead"}

    def test_the_work_belongs_to_the_firm_it_was_created_in(self, db_session, world):
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        assert project.firm_id == world.firm_a
        assert project.created_by == world.account_a2
        assert project.is_active

    def test_every_optional_field_may_be_left_empty(self, db_session, world):
        """Only the name is required (HU-3)."""
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        assert (project.description, project.address, project.estimated_start_date) == (
            None,
            None,
            None,
        )

    def test_the_client_is_assigned_in_the_same_act(self, db_session, world, new_member):
        client = new_member(world.firm_a, "clara@test.com", "client")

        project = create_project(
            db_session,
            world.firm_a,
            created_by=world.account_a2,
            name="Casa Nueva",
            client_account_id=client,
        )

        assert team(db_session, project.id) == {world.account_a2: "lead", client: "client"}

    def test_a_client_who_is_not_on_the_roster_is_refused(self, db_session, world):
        """The stale-picker case: removed from the firm while the form was open."""
        with pytest.raises(ProjectError) as refused:
            create_project(
                db_session,
                world.firm_a,
                created_by=world.account_a2,
                name="Casa Nueva",
                client_account_id=world.account_b,
            )

        assert refused.value.detail == CLIENT_NOT_ON_ROSTER

    def test_a_member_who_is_not_a_firm_client_is_refused(self, db_session, world):
        """Alba is an architect. HU-3 feeds the picker from the roster filtered
        by the client role, and the rule holds here too."""
        with pytest.raises(ProjectError) as refused:
            create_project(
                db_session,
                world.firm_a,
                created_by=world.account_a,
                name="Casa Nueva",
                client_account_id=world.account_a2,
            )

        assert refused.value.detail == CLIENT_IS_NOT_A_CLIENT

    def test_nothing_is_written_when_the_client_is_refused(self, db_session, world):
        """Checked before the project row exists, so a refusal leaves no work
        behind even if the caller never rolls back."""
        before = db_session.execute(text("SELECT count(*) FROM project")).scalar_one()

        with pytest.raises(ProjectError):
            create_project(
                db_session,
                world.firm_a,
                created_by=world.account_a2,
                name="Casa Nueva",
                client_account_id=world.account_b,
            )

        assert db_session.execute(text("SELECT count(*) FROM project")).scalar_one() == before

    def test_a_firm_client_cannot_create_a_work(self, db_session, world, new_member):
        """They would become its lead, which ADR-002 section 11.2 forbids. They
        never get here in practice — a firm client has no project.create — and
        the invariant is the service's anyway."""
        client = new_member(world.firm_a, "clara@test.com", "client")

        with pytest.raises(ProjectError) as refused:
            create_project(db_session, world.firm_a, created_by=client, name="Casa Nueva")

        assert refused.value.detail == FIRM_CLIENT_CANNOT_LEAD

    def test_the_new_work_is_visible_to_its_creator_right_away(self, db_session, world):
        """The point of doing both in one transaction, checked through the read
        that the listing actually uses."""
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        found = ProjectRepository(db_session, firm_id=world.firm_a).list_entries(
            world.account_a2, frozenset()
        )

        assert [item.project.id for item in found] == [project.id]


class TestUpdate:
    def project(self, db_session, world):
        return create_project(
            db_session,
            world.firm_a,
            created_by=world.account_a2,
            name="Casa Nueva",
            address="Calle 1",
        )

    def test_every_editable_field_is_written(self, db_session, world):
        project = self.project(db_session, world)

        update_project(
            db_session,
            project,
            name="Casa Vieja",
            description="Reforma integral",
            address="Calle 2",
            estimated_start_date=date(2026, 10, 15),
        )

        assert (project.name, project.description, project.address) == (
            "Casa Vieja",
            "Reforma integral",
            "Calle 2",
        )
        assert project.estimated_start_date == date(2026, 10, 15)

    def test_a_field_left_empty_is_cleared(self, db_session, world):
        """The form sends the whole work, so an empty address means no address
        and not "leave it alone"."""
        project = self.project(db_session, world)

        update_project(db_session, project, name="Casa Nueva")

        assert project.address is None

    def test_the_lead_is_not_touched(self, db_session, world):
        """Editing a work is not editing its team. That is HU-6."""
        project = self.project(db_session, world)

        update_project(db_session, project, name="Casa Nueva")

        assert team(db_session, project.id) == {world.account_a2: "lead"}

    def test_the_work_never_changes_firm(self, db_session, world):
        project = self.project(db_session, world)

        update_project(db_session, project, name="Casa Nueva")

        assert project.firm_id == world.firm_a


class TestUpdateTheClient:
    def project(self, db_session, world, client_account_id=None):
        return create_project(
            db_session,
            world.firm_a,
            created_by=world.account_a2,
            name="Casa Nueva",
            client_account_id=client_account_id,
        )

    def test_a_client_is_added_to_a_work_that_had_none(self, db_session, world, new_member):
        client = new_member(world.firm_a, "clara@test.com", "client")
        project = self.project(db_session, world)

        update_project(db_session, project, name="Casa Nueva", client_account_id=client)

        assert team(db_session, project.id)[client] == "client"

    def test_the_client_is_replaced_by_another(self, db_session, world, new_member):
        """Delete then insert, with a flush between: both statements in one go
        would trip uq_project_member_client, which allows one client per work."""
        first = new_member(world.firm_a, "clara@test.com", "client")
        second = new_member(world.firm_a, "cecilia@test.com", "client")
        project = self.project(db_session, world, client_account_id=first)

        update_project(db_session, project, name="Casa Nueva", client_account_id=second)

        assert team(db_session, project.id) == {world.account_a2: "lead", second: "client"}

    def test_the_client_is_cleared(self, db_session, world, new_member):
        """HU-3 says the field may stay empty, so it must be emptiable."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        project = self.project(db_session, world, client_account_id=client)

        update_project(db_session, project, name="Casa Nueva", client_account_id=None)

        assert team(db_session, project.id) == {world.account_a2: "lead"}
        assert entry(db_session, world, project.id).client is None

    def test_the_same_client_again_is_not_a_conflict(self, db_session, world, new_member):
        """The form resends the client it already has on every save."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        project = self.project(db_session, world, client_account_id=client)

        update_project(db_session, project, name="Casa Nueva", client_account_id=client)

        assert team(db_session, project.id)[client] == "client"

    def test_an_architect_cannot_become_the_client(self, db_session, world):
        project = self.project(db_session, world)

        with pytest.raises(ProjectError) as refused:
            update_project(
                db_session, project, name="Casa Nueva", client_account_id=world.account_a2
            )

        assert refused.value.detail == CLIENT_IS_NOT_A_CLIENT

    def test_a_refused_client_leaves_the_one_it_had(self, db_session, world, new_member):
        """Checked before the old assignment is removed."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        project = self.project(db_session, world, client_account_id=client)

        with pytest.raises(ProjectError):
            update_project(
                db_session, project, name="Casa Nueva", client_account_id=world.account_a2
            )

        assert team(db_session, project.id)[client] == "client"

    def test_someone_from_another_firm_cannot_become_the_client(self, db_session, world):
        """Bruno is on firm B's roster, so from firm A he is not a member at all."""
        project = self.project(db_session, world)

        with pytest.raises(ProjectError) as refused:
            update_project(
                db_session, project, name="Casa Nueva", client_account_id=world.account_b
            )

        assert refused.value.detail == CLIENT_NOT_ON_ROSTER


class TestArchive:
    def test_the_row_stays_and_only_the_flag_changes(self, db_session, world):
        """Baja lógica: the work leaves the listing, the row is still there."""
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        archive_project(db_session, project)

        assert not project.is_active
        assert (
            db_session.execute(
                text("SELECT count(*) FROM project WHERE id = :p"), {"p": project.id}
            ).scalar_one()
            == 1
        )

    def test_it_disappears_from_every_read(self, db_session, world):
        project = create_project(
            db_session, world.firm_a, created_by=world.account_a2, name="Casa Nueva"
        )

        archive_project(db_session, project)

        assert entry(db_session, world, project.id) is None

    def test_the_team_is_kept(self, db_session, world, new_member):
        """Nobody is unassigned by archiving, so restoring the work would bring
        back exactly who was on it."""
        client = new_member(world.firm_a, "clara@test.com", "client")
        project = create_project(
            db_session,
            world.firm_a,
            created_by=world.account_a2,
            name="Casa Nueva",
            client_account_id=client,
        )

        archive_project(db_session, project)

        assert team(db_session, project.id) == {world.account_a2: "lead", client: "client"}
