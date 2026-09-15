"""Platform support's screens: firms and accounts, never their content (HU-7).

Nothing here hangs off /firms/{firm_id}. Support belongs to no roster, so a route
there would resolve its membership and answer 404 to the only person meant to use
it. These routes demand platform-scope permissions instead, and the route audit in
test_route_permissions.py checks both halves: every /platform route declares a
platform permission, and none of them resolves a roster.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, requires
from app.schemas.platform import (
    FirmAdminOut,
    FirmCreate,
    FirmCreatedOut,
    FirmStatusUpdate,
    OwnerOut,
    PasswordReset,
)
from app.services.platform import (
    AccountNotFoundError,
    FirmNotFoundError,
    PlatformError,
    create_firm,
    get_firm,
    list_firms,
    reset_password,
    set_firm_active,
)

router = APIRouter(prefix="/platform", tags=["platform"])

FIRM_NOT_FOUND = "Estudio no encontrado"
ACCOUNT_NOT_FOUND = "No hay una cuenta con ese email"


@contextmanager
def _platform_rules() -> Iterator[None]:
    """Where a broken platform rule becomes a status code, for every write here.

    Same split as the roster's: 409 when the request was well formed and the
    platform's current state refuses it, 404 when the thing is not there, and
    422 left to Pydantic.

    A 404 that names the email is not an enumeration oracle here, unlike on the
    login or the roster: only support reaches this, and support can already list
    every firm on the platform.
    """
    try:
        yield
    except FirmNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=FIRM_NOT_FOUND) from None
    except AccountNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ACCOUNT_NOT_FOUND) from None
    except PlatformError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=error.detail) from None


@router.get(
    "/firms",
    response_model=list[FirmAdminOut],
    dependencies=[Depends(requires("firm.view", "platform"))],
)
def list_platform_firms(db: DbSession) -> list[FirmAdminOut]:
    """Every firm on the platform, suspended ones included, with its head count.

    firm.view in platform scope: "see any firm on the platform", which is not
    the owner's firm.view, "see the firm I am acting in" (ADR-002 section 4).
    An owner holds only the second, so an owner gets a 403 here.
    """
    return [FirmAdminOut(**vars(entry)) for entry in list_firms(db)]


@router.post(
    "/firms",
    response_model=FirmCreatedOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requires("firm.create", "platform"))],
)
def create_platform_firm(payload: FirmCreate, db: DbSession) -> FirmCreatedOut:
    """Create a firm and its owner in one transaction (ADR-002 section 10).

    One commit for both rows, after the service has flushed them together: if
    any rule refuses, nothing was written, and there is never a firm without an
    owner.

    The owner comes back as stored, with account_existed saying whether the
    address already had an account. If it did, its name and password are that
    person's and not the ones typed, and HU-7's UI tells support so.
    """
    with _platform_rules():
        created = create_firm(
            db,
            name=payload.name,
            contact_email=payload.contact_email,
            phone=payload.phone,
            owner_name=payload.owner.name,
            owner_email=payload.owner.email,
            owner_password=payload.owner.password,
        )
    db.commit()

    owner = created.owner
    return FirmCreatedOut(
        **vars(get_firm(db, created.firm.id)),
        owner=OwnerOut(
            account_id=owner.id,
            name=owner.name,
            email=owner.email,
            account_existed=created.owner_existed,
        ),
    )


@router.patch(
    "/firms/{firm_id}",
    response_model=FirmAdminOut,
    dependencies=[Depends(requires("firm.suspend", "platform"))],
)
def change_firm_status(firm_id: int, payload: FirmStatusUpdate, db: DbSession) -> FirmAdminOut:
    """Suspend or reactivate a firm, and answer with its row as the listing shows it.

    A PATCH of is_active and nothing else, which is why it demands firm.suspend
    and not firm.edit: editing a firm's data is not part of HU-7. The day it is,
    that is another body and another permission, not a wider one here.
    """
    with _platform_rules():
        set_firm_active(db, firm_id, is_active=payload.is_active)
    db.commit()

    return FirmAdminOut(**vars(get_firm(db, firm_id)))


@router.put(
    "/accounts/password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(requires("account.reset_password", "platform"))],
)
def reset_account_password(payload: PasswordReset, db: DbSession) -> None:
    """Give an account a new password, found by its email.

    A PUT on a fixed path rather than /accounts/{id}/password: support starts
    from the address the person gives on the phone, and has no screen that lists
    accounts to take an id from. The email travels in the body and never in the
    URL, where it would end up in access logs.

    204 with no body: there is nothing to show but "done".
    """
    with _platform_rules():
        reset_password(db, email=payload.email, password=payload.password)
    db.commit()
