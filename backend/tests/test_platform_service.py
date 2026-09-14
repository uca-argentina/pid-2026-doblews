"""The platform rules of HU-7, tested on the service without HTTP in the way.

The world fixture gives firm_a ana (owner) and alba (architect), and firm_b bruno
(owner). Bruno is the person who "already has an account" when support creates a
firm with his address.
"""

import pytest
from sqlalchemy import select, text

from app.core.security import verify_password
from app.models import Account, Firm, FirmMember, Role
from app.services.auth import list_firm_memberships
from app.services.platform import (
    INACTIVE_ACCOUNT_CANNOT_OWN,
    STAFF_CANNOT_OWN,
    AccountNotFoundError,
    FirmNotFoundError,
    PlatformError,
    create_firm,
    get_firm,
    list_firms,
    reset_password,
    set_firm_active,
)

TYPED_PASSWORD = "clave-inicial"


def create(db_session, owner_email: str, owner_name: str = "Nueva Dueña", name: str = "Oeste"):
    return create_firm(
        db_session,
        name=name,
        contact_email="contacto@oeste.test",
        phone="351 555-0000",
        owner_name=owner_name,
        owner_email=owner_email,
        owner_password=TYPED_PASSWORD,
    )


def owners_of(db_session, firm_id: int) -> list[FirmMember]:
    return list(
        db_session.scalars(
            select(FirmMember)
            .join(Role, Role.id == FirmMember.role_id)
            .where(FirmMember.firm_id == firm_id, Role.code == "owner", FirmMember.is_active)
        )
    )


class TestCreateFirm:
    def test_creates_the_firm_and_a_new_owner_account(self, db_session):
        firm, owner = create(db_session, "duena@oeste.test")

        assert (firm.name, firm.contact_email, firm.phone, firm.is_active) == (
            "Oeste",
            "contacto@oeste.test",
            "351 555-0000",
            True,
        )
        assert owner.name == "Nueva Dueña"
        assert verify_password(TYPED_PASSWORD, owner.password_hash)

    def test_the_new_firm_has_exactly_one_active_owner(self, db_session):
        """ADR-002 sections 10 and 11.1: never a firm nobody can enter."""
        firm, owner = create(db_session, "duena@oeste.test")

        assert [member.account_id for member in owners_of(db_session, firm.id)] == [owner.id]

    def test_the_owner_can_act_in_the_new_firm_right_away(self, db_session):
        firm, owner = create(db_session, "duena@oeste.test")

        memberships = list_firm_memberships(db_session, owner.id)

        assert [(m.firm_id, m.role_code) for m in memberships] == [(firm.id, "owner")]

    def test_an_existing_account_becomes_owner_as_it_is(self, db_session, world):
        """HU-7: "se lo asigna como propietario sin crear una cuenta nueva"."""
        before = db_session.get(Account, world.account_b)
        hash_before = before.password_hash
        accounts_before = db_session.scalar(select(Account.id).order_by(Account.id.desc()))

        firm, owner = create(db_session, "bruno@test.com", owner_name="Otro Nombre")

        assert owner.id == world.account_b
        assert owner.name == "bruno"
        assert owner.password_hash == hash_before
        assert db_session.scalar(select(Account.id).order_by(Account.id.desc())) == accounts_before
        # Bruno now owns two firms, each with its own roster row.
        firms = {m.firm_id for m in list_firm_memberships(db_session, world.account_b)}
        assert firms == {world.firm_b, firm.id}

    def test_refuses_a_staff_account_and_writes_nothing(self, db_session, support_account):
        """ADR-002 section 11.4: support cannot hand itself a firm role."""
        firms_before = db_session.scalar(select(Firm.id).order_by(Firm.id.desc()))

        with pytest.raises(PlatformError) as error:
            create(db_session, "soporte@test.com")

        assert error.value.detail == STAFF_CANNOT_OWN
        assert db_session.scalar(select(Firm.id).order_by(Firm.id.desc())) == firms_before

    def test_refuses_a_deactivated_account(self, db_session, db, world):
        """It could not log in, so the firm would be one nobody can enter."""
        db.execute(
            text("UPDATE account SET is_active = false WHERE id = :id"), {"id": world.account_b}
        )

        with pytest.raises(PlatformError) as error:
            create(db_session, "bruno@test.com")

        assert error.value.detail == INACTIVE_ACCOUNT_CANNOT_OWN


class TestListFirms:
    def test_lists_every_firm_ordered_by_name_with_its_active_members(self, db_session, world):
        entries = [(firm.name, firm.member_count) for firm in list_firms(db_session)]

        # norte has ana and alba, sur has bruno.
        assert entries == [("norte", 2), ("sur", 1)]

    def test_people_who_left_are_not_counted(self, db_session, world, new_member):
        new_member(world.firm_a, "se-fue@test.com", "architect", is_active=False)

        assert get_firm(db_session, world.firm_a).member_count == 2

    def test_a_firm_with_nobody_active_counts_zero_and_is_still_listed(self, db_session, db, world):
        db.execute(
            text("UPDATE firm_member SET is_active = false WHERE firm_id = :f"),
            {"f": world.firm_b},
        )

        assert get_firm(db_session, world.firm_b).member_count == 0
        assert "sur" in [firm.name for firm in list_firms(db_session)]

    def test_suspended_firms_are_listed_as_such(self, db_session, world):
        """The listing is where support finds a firm to reactivate."""
        set_firm_active(db_session, world.firm_b, is_active=False)

        states = {firm.name: firm.is_active for firm in list_firms(db_session)}

        assert states == {"norte": True, "sur": False}

    def test_an_unknown_firm_is_not_found(self, db_session):
        with pytest.raises(FirmNotFoundError):
            get_firm(db_session, 999_999)


class TestSetFirmActive:
    def test_suspending_locks_the_members_out(self, db_session, world):
        set_firm_active(db_session, world.firm_a, is_active=False)

        assert list_firm_memberships(db_session, world.account_a) == []
        assert list_firm_memberships(db_session, world.account_a2) == []

    def test_reactivating_brings_everything_back_as_it_was(self, db_session, world):
        set_firm_active(db_session, world.firm_a, is_active=False)
        set_firm_active(db_session, world.firm_a, is_active=True)

        memberships = list_firm_memberships(db_session, world.account_a)

        assert [(m.firm_id, m.role_code) for m in memberships] == [(world.firm_a, "owner")]

    def test_is_idempotent(self, db_session, world):
        set_firm_active(db_session, world.firm_a, is_active=False)

        firm = set_firm_active(db_session, world.firm_a, is_active=False)

        assert firm.is_active is False

    def test_leaves_the_other_firms_alone(self, db_session, world):
        set_firm_active(db_session, world.firm_a, is_active=False)

        assert [m.firm_id for m in list_firm_memberships(db_session, world.account_b)] == [
            world.firm_b
        ]

    def test_an_unknown_firm_is_not_found(self, db_session):
        with pytest.raises(FirmNotFoundError):
            set_firm_active(db_session, 999_999, is_active=False)


class TestResetPassword:
    def test_replaces_the_password(self, db_session, world):
        reset_password(db_session, email="ana@test.com", password="clave-nueva")

        account = db_session.get(Account, world.account_a)
        assert verify_password("clave-nueva", account.password_hash)

    def test_does_not_bring_back_a_deactivated_account(self, db_session, db, world):
        db.execute(
            text("UPDATE account SET is_active = false WHERE id = :id"), {"id": world.account_a}
        )

        reset_password(db_session, email="ana@test.com", password="clave-nueva")

        assert db_session.get(Account, world.account_a).is_active is False

    def test_an_unknown_address_is_not_found(self, db_session):
        with pytest.raises(AccountNotFoundError):
            reset_password(db_session, email="nadie@test.com", password="clave-nueva")

    def test_a_staff_account_is_not_found(self, db_session, support_account):
        """Resetting another support's password would be a way into
        platform_member's power without writing a row there."""
        hash_before = db_session.get(Account, support_account).password_hash

        with pytest.raises(AccountNotFoundError):
            reset_password(db_session, email="soporte@test.com", password="clave-nueva")

        assert db_session.get(Account, support_account).password_hash == hash_before
