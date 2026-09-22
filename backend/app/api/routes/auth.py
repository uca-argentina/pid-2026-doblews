"""Logging in, and answering "who am I" for the rest of the session."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentAccount, DbSession
from app.core.token import create_access_token
from app.schemas.auth import LoginRequest, MeResponse, TokenResponse
from app.schemas.firm import FirmSummary, RoleOut
from app.services.auth import authenticate, list_firm_memberships, list_platform_roles
from app.services.authz import platform_permissions

router = APIRouter(prefix="/auth", tags=["auth"])

# One message for every way a login can fail. Spanish because it is rendered as
# typed, and a constant so the tests assert against the same string the endpoint
# returns rather than a copy that can drift.
INVALID_CREDENTIALS = "Email o contraseña incorrectos"


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    """Exchange an email and password for an access token.

    Takes JSON rather than FastAPI's OAuth2PasswordRequestForm: that form would
    force the field to be called `username` when our identity is an email, and
    make this the one endpoint in the API that is not JSON, in exchange for the
    Authorize button in /docs — which HTTPBearer gives us anyway. We are not
    implementing OAuth2, and HU-1 puts it out of scope.

    Returns only the token. The frontend then calls /auth/me, so that "who am I"
    has a single code path shared by the login and by reloading the page: a bug
    in the roster query shows up in both instead of hiding in one.
    """
    account = authenticate(db, email=payload.email, password=payload.password)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
        )

    return TokenResponse(access_token=create_access_token(account.id))


@router.get("/me", response_model=MeResponse)
def read_current_account(account: CurrentAccount, db: DbSession) -> MeResponse:
    """The session as the frontend needs it: who I am and where I can act.

    Called once when the app boots with a stored token, which is what makes the
    session survive a reload.

    response_model is what keeps password_hash off the wire even if this
    function ever starts returning the ORM object.
    """
    memberships = list_firm_memberships(db, account_id=account.id)

    return MeResponse(
        id=account.id,
        name=account.name,
        email=account.email,
        platform_roles=list_platform_roles(db, account_id=account.id),
        platform_permissions=sorted(platform_permissions(db, account.id)),
        firms=[
            FirmSummary(
                id=membership.firm_id,
                name=membership.firm_name,
                role=RoleOut(code=membership.role_code, name=membership.role_name),
            )
            for membership in memberships
        ],
    )
