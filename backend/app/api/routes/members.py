"""The firm roster: who works in this firm, and with which role (HU-2)."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentAccount, CurrentMembership, DbSession, requires
from app.repositories.member import FirmMemberRepository, RosterEntry
from app.schemas.firm import RoleOut
from app.schemas.member import MemberCreate, MemberOut, MemberRoleUpdate
from app.services.roster import (
    MemberNotFoundError,
    RosterError,
    add_member,
    change_member_role,
    list_assignable_roles,
    remove_member,
)

router = APIRouter(prefix="/firms/{firm_id}/members", tags=["members"])

MEMBER_NOT_FOUND = "Miembro no encontrado"


@contextmanager
def _roster_rules() -> Iterator[None]:
    """Where a broken roster rule becomes a status code, for every write here.

    409 Conflict and not 422 for a refused rule: the request was well formed, it
    is the roster's current state that refuses it. 422 stays for what Pydantic
    rejects. A member that is not there — in this firm, active — is a 404, the
    same one whatever the reason.
    """
    try:
        yield
    except MemberNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MEMBER_NOT_FOUND) from None
    except RosterError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


def _to_member_out(entry: RosterEntry) -> MemberOut:
    return MemberOut(
        account_id=entry.account_id,
        name=entry.name,
        email=entry.email,
        role=RoleOut(code=entry.role_code, name=entry.role_name),
        is_active=entry.is_active,
        joined_at=entry.joined_at,
    )


@router.get(
    "",
    response_model=list[MemberOut],
    dependencies=[Depends(requires("member.view", "firm"))],
)
def list_members(membership: CurrentMembership, db: DbSession) -> list[MemberOut]:
    """Everyone on the roster, the people who left included, with their state.

    member.view and not one of the management permissions, so an architect gets
    a 200 here: HU-3 fills its client picker from this roster, and architects
    create projects. HU-2's "an architect gets 403" is about the roster section,
    which the frontend gates on member.add, and about the three endpoints that
    change the roster.

    The firm comes from the resolved membership and never from the raw path, so
    the repository is built with a firm the caller has already proved they
    belong to.
    """
    members = FirmMemberRepository(db, firm_id=membership.firm_id)
    return [_to_member_out(entry) for entry in members.list_roster()]


@router.post(
    "",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("member.add", "firm"))],
)
def add_member_to_roster(
    payload: MemberCreate, membership: CurrentMembership, db: DbSession
) -> MemberOut:
    """Add someone to the roster, or bring back someone who left.

    The same 201 and the same shape whether the address already had an account
    or not (HU-2). What comes back is the member as stored, so if the account
    existed its name is the person's own, not the one typed: joining a roster
    means this firm sees it from now on, and HU-2 asks the UI to say so.

    The only 409 is about this firm's roster ("already a member"), never about
    the platform: there is no "that email is taken".
    """
    with _roster_rules():
        member = add_member(
            db,
            membership.firm_id,
            name=payload.name,
            email=payload.email,
            role_code=payload.role_code,
            password=payload.password,
        )
    db.commit()

    return _to_member_out(
        FirmMemberRepository(db, firm_id=membership.firm_id).entry(member.account_id)
    )


@router.get(
    "/roles",
    response_model=list[RoleOut],
    dependencies=[Depends(requires("member.add", "firm"))],
)
def list_member_roles(db: DbSession) -> list[RoleOut]:
    """The roles the add and edit forms offer: architect and client, never owner.

    member.add because the only screen that needs them is the one that adds
    people; the edit form sits beside it, behind the same section.
    """
    return [RoleOut(code=role.code, name=role.name) for role in list_assignable_roles(db)]


@router.patch(
    "/{account_id}",
    response_model=MemberOut,
    dependencies=[Depends(requires("member.edit_role", "firm"))],
)
def change_role(
    account_id: int,
    payload: MemberRoleUpdate,
    account: CurrentAccount,
    membership: CurrentMembership,
    db: DbSession,
) -> MemberOut:
    """Change an active member's firm role. The only field this edits.

    The caller's own account comes in as the actor, because "you cannot change
    your own role" needs to know who is asking. CurrentAccount is already
    resolved for the permission check, so it costs nothing here.
    """
    with _roster_rules():
        change_member_role(
            db,
            membership.firm_id,
            actor_id=account.id,
            account_id=account_id,
            role_code=payload.role_code,
        )
    db.commit()

    return _to_member_out(FirmMemberRepository(db, firm_id=membership.firm_id).entry(account_id))


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("member.remove", "firm"))],
)
def remove_from_roster(
    account_id: int,
    account: CurrentAccount,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    """Take someone off the roster. A logical removal, not a DELETE in the database.

    The HTTP verb says what happens from the API's point of view: the membership
    is gone, and the listing shows it as inactive from now on. In the database it
    is an UPDATE of firm_member.is_active; the team rule against deleting rows is
    about SQL, and nothing is deleted here. Adding the same address again brings
    the person back, projects included.

    204 with no body: the frontend already has the row and only flips its state.
    """
    with _roster_rules():
        remove_member(db, membership.firm_id, actor_id=account.id, account_id=account_id)
    db.commit()
