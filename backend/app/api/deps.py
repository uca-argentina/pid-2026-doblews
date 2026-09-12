"""The border where "nothing found" becomes an HTTP status code.

Implements the request resolution of ADR-002 section 9: who is asking, which
firm they are asking about, and whether their roles there grant what the route
demands. The permissions themselves are resolved in app/services/authz.py; this
module only turns an answer into a status code.

Status codes live here and nowhere else, so the rule "someone else's resource is
a 404, never a 403" is enforced in one place instead of per endpoint.

Dependencies are written as Annotated aliases rather than as argument defaults:
FastAPI's own recommended style, it keeps ruff's B008 happy, and it lets a route
declare `account: CurrentAccount` instead of restating the Depends() every time.
"""

import inspect
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.token import decode_access_token
from app.db.session import get_db
from app.models import Account
from app.services.auth import FirmMembership, get_firm_membership
from app.services.authz import (
    VIEW_ALL,
    Scope,
    firm_permissions,
    platform_permissions,
    project_permissions,
)

# auto_error=False because with the default FastAPI answers a missing header
# with 403, and the frontend tells the two apart: 401 means the session is gone
# and it should show the login, 403 means logged in but not allowed. We raise
# the 401 ourselves below.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = "No pudimos validar tu sesión"
FIRM_NOT_FOUND = "Estudio no encontrado"
PROJECT_NOT_FOUND = "Obra no encontrada"
FORBIDDEN = "No tenés permiso para hacer esto"

# Stamped on every dependency requires_any() builds, so the route table can be
# asked which permission each endpoint demands. Nothing authorizes with it; it is
# what makes the deny-by-default rule in backend/CLAUDE.md a test instead of a
# promise.
#
# Always a tuple of (code, scope) pairs, even for the one-permission case, so an
# auditor walking the route table reads one shape and never has to tell "a pair"
# from "a tuple of pairs" by inspecting it.
REQUIRED_PERMISSION = "required_permission"

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


def get_platform_permissions(account: CurrentAccount, db: DbSession) -> frozenset[str]:
    """What the caller may do to the platform itself. Empty for almost everyone."""
    return platform_permissions(db, account.id)


def get_firm_permissions(membership: CurrentMembership, db: DbSession) -> frozenset[str]:
    """What the caller may do inside the firm named by the URL.

    Depending on CurrentMembership is what orders the failures correctly: an
    anonymous caller is refused with 401 and an outsider with 404, both before
    any permission is looked at.
    """
    return firm_permissions(db, membership.role_id)


def get_project_permissions(
    account: CurrentAccount,
    membership: CurrentMembership,
    db: DbSession,
    # Declared explicitly for the same reason as firm_id above: an undeclared
    # parameter would be read as a query parameter.
    project_id: Annotated[int, Path()],
) -> frozenset[str]:
    """What the caller may do inside the project named by the URL.

    The firm comes from the already-resolved membership and never from the
    request, so a project belonging to another firm resolves to no permissions
    at all rather than to someone else's.

    An empty set is where the work stops being a 403 and becomes a 404. HU-3:
    "Si pido por URL una obra ajena —de otro miembro o de otro estudio— recibo
    404 (no 403 — no revelamos que existe)." Nothing at all in this project, and
    no firm-wide project.view_all to widen it, means the caller cannot see the
    work exists, and four situations collapse into the same answer: no such
    project, another firm's project, an archived one, and one of this firm they
    were never put on.

    Holding *something* here and not the permission the route demands is the
    other case, and stays a 403: they can already see the work, so hiding it
    protects nothing. That is what HU-6 asks for when a collaborator tries to
    change the team.
    """
    granted = project_permissions(
        db, account_id=account.id, project_id=project_id, firm_id=membership.firm_id
    )
    if not granted and VIEW_ALL not in firm_permissions(db, membership.role_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PROJECT_NOT_FOUND)

    return granted


# Routes that need to read the set — the repositories do, to answer "which rows?"
# — declare one of these. Routes that only need to be guarded use requires().
PlatformPermissions = Annotated[frozenset[str], Depends(get_platform_permissions)]
FirmPermissions = Annotated[frozenset[str], Depends(get_firm_permissions)]
ProjectPermissions = Annotated[frozenset[str], Depends(get_project_permissions)]

_PERMISSIONS_BY_SCOPE: dict[str, object] = {
    "platform": PlatformPermissions,
    "firm": FirmPermissions,
    "project": ProjectPermissions,
}


def requires_any(*needed: tuple[str, Scope]) -> Callable[..., None]:
    """Declare that any one of these permissions opens the endpoint.

        @router.get("/{firm_id}/projects/{project_id}",
                    dependencies=[Depends(requires_any(
                        ("project.view", "project"),
                        ("project.view_all", "firm"),
                    ))])

    The OR exists because a capability can be granted at two different heights.
    That is the case HU-3 puts on the table: reading one project is a project
    permission, but the owner's right to read *every* project of their firm is a
    firm one (ADR-002 section 7, "project.view_all es de ámbito estudio"), and
    the owner has no project_member row to resolve a project permission from.
    Writing the alternative here keeps both halves as rows of the seed; the
    other way out — teaching the resolver that one permission implies another —
    would move a grant into code, which is exactly what that section avoids.

    Declaring the alternative is not the same as widening the tenant. Whichever
    branch lets the caller in, which *rows* they then see is still the
    repository's answer, never this one (section 8).

    The signature is built rather than written because the parameters depend on
    the scopes asked for, and FastAPI resolves dependencies by reading
    inspect.signature(). One parameter per distinct scope, so a route naming the
    same scope twice still costs a single query.
    """
    if not needed:
        raise ValueError("requires_any() needs at least one (code, scope) pair")

    scopes = sorted({scope for _, scope in needed})
    unknown = [scope for scope in scopes if scope not in _PERMISSIONS_BY_SCOPE]
    if unknown:
        raise ValueError(
            f"unknown scope {unknown[0]!r}; expected one of {sorted(_PERMISSIONS_BY_SCOPE)}"
        )

    def guard(**granted: frozenset[str]) -> None:
        if not any(code in granted[scope] for code, scope in needed):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN)

    # Keyword-only, and named after the scope, so guard() can look each set up by
    # the same string the (code, scope) pairs carry.
    guard.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [
            inspect.Parameter(
                scope,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=_PERMISSIONS_BY_SCOPE[scope],
            )
            for scope in scopes
        ]
    )

    setattr(guard, REQUIRED_PERMISSION, tuple(needed))
    return guard


def requires(code: str, scope: Scope) -> Callable[..., None]:
    """Declare the permission an endpoint demands. Deny by default.

        @router.get("/{firm_id}/members",
                    dependencies=[Depends(requires("member.view", "firm"))])

    Both arguments are needed because a code only identifies a capability inside
    a scope: firm.view exists in platform scope and in firm scope, and they are
    different permissions — one is "see any firm on the platform", the other is
    "see the firm I am acting in" (ADR-002 section 4).

    The three failures come out in the right order without a single extra
    condition, because the permission dependencies hang off the identity and
    membership ones:

        no token          -> 401
        not on the roster -> 404, never 403, since a 403 would confirm the firm
                             exists (ADR-002 section 9)
        member, no grant  -> 403, which is what HU-2 and HU-6 ask for: the caller
                             already knows the firm exists, so hiding it protects
                             nothing and only confuses

    Costs one query per scope per request, however many permissions a route
    demands: every guard depends on the same module-level function object, and
    FastAPI caches a dependency's result for the duration of a request.

    An unknown scope raises at import time, when the route is declared, rather
    than on the first request that reaches it.

    The single-permission case of requires_any, which is the common one by far:
    most endpoints answer to exactly one capability, and reading the OR version
    at every route would suggest a choice that is not being made.
    """
    return requires_any((code, scope))
