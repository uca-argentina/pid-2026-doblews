"""Every route, audited against the promises the project made about access.

backend/CLAUDE.md says "endpoint sin permiso declarado no responde" and ADR-002
lists "una suite de tests de aislamiento entre estudios, con al menos un caso por
endpoint" among the commitments taken on. Both are promises about routes that do
not exist yet, so they cannot be kept by remembering: they are kept by walking
the route table and failing when something new does not comply.

modelo-datos-sprint-1.md section 6 asks for exactly this: "Conviene parametrizarlo
sobre la tabla de rutas de FastAPI para que un endpoint nuevo quede cubierto solo."
"""

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.api.deps import REQUIRED_PERMISSION, get_current_membership
from app.main import app

# Routes that legitimately demand no permission, each with the reason. Adding a
# line here is a deliberate act, which is the point: the default is to be caught.
NO_PERMISSION_REQUIRED = {
    "GET /health": "Liveness probe for the deploy. Returns nobody's data.",
    "POST /auth/login": "Where a session is obtained. Demanding one first would be circular.",
    "GET /auth/me": (
        "Identity, not authorization: it answers who the token belongs to and which firms "
        "are open to them. There is no permission to demand, and what it returns is already "
        "filtered to the caller's own roster rows."
    ),
    "GET /units-of-measure": (
        "Global platform catalogue (HU-0, ADR-003 section 7): no firm_id/project_id in the "
        "path, so there is no scope to hang a requires(...) permission off. Every firm role "
        "needs to read it to fill a 'unidad' field, and it holds no firm's data."
    ),
}

# How to build a URL for a route that takes path parameters. A parameter missing
# from here fails the isolation test below rather than quietly skipping it, so a
# new kind of id has to be added on purpose.
PATH_PARAMETERS = {
    "firm_id": lambda world: world.firm_a,
    "project_id": lambda world: world.project_a,
    # Deliberately an id that exists nowhere. Every route taking one resolves the
    # firm and then the work first, so a stranger is refused before the version
    # is ever looked up — which is the whole point of the test below. Building a
    # real one would mean saving a budget version inside this fixture, making an
    # isolation test depend on HU-12's write path.
    "version_id": lambda world: 1,
}


@dataclass(frozen=True)
class Endpoint:
    """One method of one route, with the dependency tree FastAPI built for it."""

    method: str
    path: str
    dependant: Dependant

    def __str__(self) -> str:
        return f"{self.method} {self.path}"


def _endpoints(application: FastAPI) -> list[Endpoint]:
    """Every route the app actually serves, prefixes already applied.

    Walking app.routes alone is not enough and fails open, which is worse than
    failing loudly: FastAPI stores an included router as a single lazy object and
    only materialises its routes on demand, so a naive walk would find /health,
    audit nothing else, and pass. effective_route_contexts() flattens that tree.

    Starlette's own /docs, /redoc and /openapi.json are not APIRoutes and drop
    out here, which is right: they are the framework's, not ours.
    """
    found: list[Endpoint] = []

    def collect(path: str, methods: set[str], dependant: Dependant) -> None:
        for method in sorted(methods - {"HEAD", "OPTIONS"}):
            found.append(Endpoint(method, path, dependant))

    for route in application.routes:
        if isinstance(route, APIRoute):
            collect(route.path, route.methods, route.dependant)
        elif hasattr(route, "effective_route_contexts"):
            for context in route.effective_route_contexts():
                collect(context.path, set(context.methods), context.dependant)

    return found


def _walk(dependant: Dependant):
    """The dependency and everything it depends on, however deep."""
    yield dependant
    for sub in dependant.dependencies:
        yield from _walk(sub)


def _declared_permissions(endpoint: Endpoint) -> list[tuple[str, str]]:
    return [
        marker
        for dependant in _walk(endpoint.dependant)
        if (marker := getattr(dependant.call, REQUIRED_PERMISSION, None)) is not None
    ]


def _depends_on(endpoint: Endpoint, dependency) -> bool:
    return any(dependant.call is dependency for dependant in _walk(endpoint.dependant))


ENDPOINTS = _endpoints(app)

# Two families of routes that take a firm_id and must never be confused. Inside a
# firm, the caller acts as a member and the roster decides whether the firm exists
# for them. On the platform, support acts on firms from outside, belongs to no
# roster, and resolving one would lock out the only person meant to get in (HU-7).
FIRM_PREFIX = "/firms/{firm_id}"
PLATFORM_PREFIX = "/platform/"

FIRM_SCOPED = [endpoint for endpoint in ENDPOINTS if endpoint.path.startswith(FIRM_PREFIX)]
PLATFORM_SCOPED = [endpoint for endpoint in ENDPOINTS if endpoint.path.startswith(PLATFORM_PREFIX)]


def test_the_route_table_was_actually_read():
    """Guards the guard. If the walk above ever stops finding the included
    routers, every test below would pass by auditing an empty list."""
    paths = {endpoint.path for endpoint in ENDPOINTS}

    assert {"/auth/login", "/auth/me", "/firms/{firm_id}", "/platform/firms"} <= paths
    assert FIRM_SCOPED, "no firm-scoped route found; the walk is broken"
    assert PLATFORM_SCOPED, "no platform route found; the walk is broken"


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=str)
def test_every_route_taking_a_firm_id_belongs_to_an_audited_family(endpoint):
    """Grouping by prefix must not fail open.

    A route like /reports/{firm_id} would be neither firm-scoped nor platform
    by prefix, and would escape both audits below while reading a firm_id
    straight from the URL. It has to pick a family on purpose.
    """
    if "{firm_id}" not in endpoint.path:
        return

    assert endpoint.path.startswith((FIRM_PREFIX, PLATFORM_PREFIX)), (
        f"{endpoint} takes a firm_id outside {FIRM_PREFIX} and {PLATFORM_PREFIX}, "
        f"so no audit covers it. Move it under one of them."
    )


def test_the_audit_reports_an_endpoint_that_complies_with_neither():
    """Guards the guard, from the other side.

    The tests below assert that something is present. If the two auditors ever
    stopped detecting anything at all — a renamed marker, a changed dependency
    tree — those assertions would keep passing on compliant routes and quietly
    stop catching anything. This points them at a route that deliberately breaks
    both rules and checks they notice.
    """
    unguarded = FastAPI()

    @unguarded.get("/firms/{firm_id}/secrets")
    def leak() -> dict[str, str]:
        return {"everything": "of every firm"}

    endpoints = _endpoints(unguarded)

    assert [str(endpoint) for endpoint in endpoints] == ["GET /firms/{firm_id}/secrets"]
    assert _declared_permissions(endpoints[0]) == []
    assert not _depends_on(endpoints[0], get_current_membership)


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=str)
def test_every_endpoint_declares_the_permission_it_demands(endpoint):
    """Deny by default, checked instead of remembered.

    A new endpoint that forgets Depends(requires(...)) fails here, in its own
    pull request, rather than shipping open.
    """
    if str(endpoint) in NO_PERMISSION_REQUIRED:
        pytest.skip(NO_PERMISSION_REQUIRED[str(endpoint)])

    assert _declared_permissions(endpoint), (
        f"{endpoint} declares no permission. Add Depends(requires(code, scope)), or add it "
        f"to NO_PERMISSION_REQUIRED with the reason if it truly needs none."
    )


@pytest.mark.parametrize("endpoint", FIRM_SCOPED, ids=str)
def test_every_firm_scoped_endpoint_resolves_the_roster(endpoint):
    """Having a permission is not having a tenant.

    Without this dependency an endpoint would read {firm_id} straight from the
    URL and trust it, which is how one firm ends up reading another's rows.
    """
    assert _depends_on(
        endpoint, get_current_membership
    ), f"{endpoint} takes a firm_id from the URL without resolving it against the roster."


@pytest.mark.parametrize("endpoint", [e for e in FIRM_SCOPED if e.method == "GET"], ids=str)
def test_a_stranger_gets_404_from_every_firm_scoped_endpoint(endpoint, client, world, auth_header):
    """The isolation case ADR-002 section 8 asks for, once per endpoint.

    Bruno belongs to firm_b and asks firm_a for something. 404 and never 403,
    because a 403 would confirm the firm exists.

    Only GET routes are exercised: the others would need a valid body to reach
    the dependency at all. They are still covered by the two static tests above,
    and the dependency's own behaviour is pinned in test_requires.py.
    """
    response = client.get(_url(endpoint, world), headers=auth_header(world.account_b))

    assert response.status_code == 404, f"{endpoint} answered {response.status_code} to an outsider"


@pytest.mark.parametrize("endpoint", PLATFORM_SCOPED, ids=str)
def test_every_platform_endpoint_demands_only_platform_permissions(endpoint):
    """ADR-002 section 4: firm.view exists in platform scope and in firm scope,
    and they are different permissions. A /platform route guarded with the firm
    one would open support's screens to every owner, who holds it."""
    scopes = {scope for declared in _declared_permissions(endpoint) for _, scope in declared}

    assert scopes == {
        "platform"
    }, f"{endpoint} demands permissions in {sorted(scopes)}; support routes demand 'platform'."


@pytest.mark.parametrize("endpoint", PLATFORM_SCOPED, ids=str)
def test_no_platform_endpoint_resolves_a_roster(endpoint):
    """The mirror of the firm-scoped audit. Support is on no roster, so a
    platform route that resolved one would 404 the only person meant to use it,
    and would be a sign it is reaching into a firm instead of acting on it."""
    assert not _depends_on(
        endpoint, get_current_membership
    ), f"{endpoint} resolves a firm roster; platform routes act on firms from outside."


@pytest.mark.parametrize("endpoint", [e for e in PLATFORM_SCOPED if e.method == "GET"], ids=str)
def test_an_owner_gets_403_from_every_platform_endpoint(endpoint, client, world, auth_header):
    """Holding firm.view in one's own firm is not holding it on the platform.

    403 and not 404: support's screens are no secret, and there is no tenant to
    hide. What must not happen is a 200.
    """
    response = client.get(_url(endpoint, world), headers=auth_header(world.account_a))

    assert response.status_code == 403, f"{endpoint} answered {response.status_code} to an owner"


def _url(endpoint: Endpoint, world) -> str:
    """The route's path with every parameter filled in from the world fixture."""
    unknown = [name for name in _path_parameter_names(endpoint.path) if name not in PATH_PARAMETERS]
    assert not unknown, (
        f"{endpoint} takes path parameters this test cannot build: {unknown}. "
        f"Add them to PATH_PARAMETERS so the route is really exercised."
    )

    url = endpoint.path
    for name in _path_parameter_names(endpoint.path):
        url = url.replace(f"{{{name}}}", str(PATH_PARAMETERS[name](world)))
    return url


def _path_parameter_names(path: str) -> list[str]:
    return [part.split("}")[0] for part in path.split("{")[1:]]


# --- a saved budget version is never edited ---------------------------------


def test_the_budget_versions_prefix_offers_no_way_to_change_a_version():
    """ADR-007 section 5, rule 2, as topology rather than as a check.

    HU-12 asks that a saved version never be modified. That is not enforced by a
    permission or by a service refusing something: it is enforced by there being
    no endpoint to call. A rule kept by the absence of code is exactly the kind
    that comes back by accident — someone adds a PATCH to "fix a typo in the
    note" and nothing else in the system objects — so the absence is asserted
    here, in the same language modelo-datos section 6 uses for the rest of the
    route table.

    Four routes, no more: create, list, read, and load back into the draft.
    Loading is a POST and writes the *take-off*, never the version.
    """
    prefix = "/firms/{firm_id}/projects/{project_id}/budget/versions"
    offered = {
        (endpoint.method, endpoint.path)
        for endpoint in ENDPOINTS
        if endpoint.path.startswith(prefix)
    }

    assert offered == {
        ("POST", prefix),
        ("GET", prefix),
        ("GET", f"{prefix}/{{version_id}}"),
        ("POST", f"{prefix}/{{version_id}}/load"),
    }
