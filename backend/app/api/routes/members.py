"""The firm roster: who works in this firm, and with which role (HU-2)."""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentMembership, DbSession, requires
from app.repositories.member import FirmMemberRepository, RosterEntry
from app.schemas.firm import RoleOut
from app.schemas.member import MemberCreate, MemberOut
from app.services.roster import RosterError, add_member, list_assignable_roles

router = APIRouter(prefix="/firms/{firm_id}/members", tags=["members"])


@contextmanager
def _roster_rules() -> Iterator[None]:
    """Where a broken roster rule becomes a status code, for every write here.

    409 Conflict and not 422: the request was well formed, it is the roster's
    current state that refuses it. 422 stays for what Pydantic rejects.
    """
    try:
        yield
    except RosterError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error.detail) from None


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
