"""The border where "nothing found" becomes an HTTP status code.

Implements the first two steps of the request resolution in ADR-002 section 9:
who is asking, and which firm they are asking about. Step three, resolving the
permissions themselves, is T-03 and lands next to these.

Status codes live here and nowhere else, so the rule "someone else's resource is
a 404, never a 403" is enforced in one place instead of per endpoint.

Dependencies are written as Annotated aliases rather than as argument defaults:
FastAPI's own recommended style, it keeps ruff's B008 happy, and it lets a route
declare `account: CurrentAccount` instead of restating the Depends() every time.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.token import decode_access_token
from app.db.session import get_db
from app.models import Account
from app.services.auth import FirmMembership, get_firm_membership

# auto_error=False because with the default FastAPI answers a missing header
# with 403, and the frontend tells the two apart: 401 means the session is gone
# and it should show the login, 403 means logged in but not allowed. We raise
# the 401 ourselves below.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = "No pudimos validar tu sesión"
FIRM_NOT_FOUND = "Estudio no encontrado"

DbSession = Annotated[Session, Depends(get_db)]
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_current_account(credentials: BearerToken, db: DbSession) -> Account:
    """The account behind the bearer token, freshly read from the database.

    Reading the row rather than trusting the token is the whole point of
    ADR-002 section 9: it is what makes deactivating someone take effect on
    their very next request instead of whenever their token happens to expire.

    Missing, malformed, expired and forged tokens all give the same 401 as a
    deactivated account, since distinguishing them only helps an attacker.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=CREDENTIALS_ERROR,
        # Required by RFC 7235 on a 401, and what tells a client which scheme to
        # retry with.
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    account_id = decode_access_token(credentials.credentials)
    if account_id is None:
        raise unauthorized

    # get() and not a select(): this is a primary key lookup, so it can be
    # served straight from the session's identity map.
    account = db.get(Account, account_id)
    if account is None or not account.is_active:
        raise unauthorized

    return account


CurrentAccount = Annotated[Account, Depends(get_current_account)]


def get_current_membership(
    account: CurrentAccount,
    db: DbSession,
    # Declared explicitly because FastAPI reads an undeclared dependency
    # parameter as a query parameter, not as part of the path.
    firm_id: Annotated[int, Path()],
) -> FirmMembership:
    """The caller's roster row in the firm named by the URL.

    The active firm comes from the path and never from the session or the token
    (ADR-002 section 9), so two tabs can sit in two different firms without one
    silently writing into the other.

    Four different situations answer with the same 404 — never a member, left
    the roster, firm suspended, firm does not exist — because a 403 would
    confirm that the firm exists, and the firms of a competing studio are
    exactly what must stay invisible.

    Depending on the account means an anonymous request gets a 401 before this
    runs, which is what the frontend needs to send it to the login.

    Every route using this must name its path parameter firm_id.
    """
    membership = get_firm_membership(db, account_id=account.id, firm_id=firm_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=FIRM_NOT_FOUND)

    return membership


CurrentMembership = Annotated[FirmMembership, Depends(get_current_membership)]
