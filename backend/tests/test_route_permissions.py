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
}

# How to build a URL for a route that takes path parameters. A parameter missing
# from here fails the isolation test below rather than quietly skipping it, so a
# new kind of id has to be added on purpose.
PATH_PARAMETERS = {
    "firm_id": lambda world: world.firm_a,
    "project_id": lambda world: world.project_a,
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
FIRM_SCOPED = [endpoint for endpoint in ENDPOINTS if "{firm_id}" in endpoint.path]


def test_the_route_table_was_actually_read():
    """Guards the guard. If the walk above ever stops finding the included
    routers, every test below would pass by auditing an empty list."""
    paths = {endpoint.path for endpoint in ENDPOINTS}

    assert {"/auth/login", "/auth/me", "/firms/{firm_id}"} <= paths
    assert FIRM_SCOPED, "no firm-scoped route found; the walk is broken"


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
    unknown = [name for name in _path_parameter_names(endpoint.path) if name not in PATH_PARAMETERS]
    assert not unknown, (
        f"{endpoint} takes path parameters this test cannot build: {unknown}. "
        f"Add them to PATH_PARAMETERS so the route is really exercised."
    )

    url = endpoint.path
    for name in _path_parameter_names(endpoint.path):
        url = url.replace(f"{{{name}}}", str(PATH_PARAMETERS[name](world)))

    response = client.get(url, headers=auth_header(world.account_b))

    assert response.status_code == 404, f"{endpoint} answered {response.status_code} to an outsider"


def _path_parameter_names(path: str) -> list[str]:
    return [part.split("}")[0] for part in path.split("{")[1:]]
