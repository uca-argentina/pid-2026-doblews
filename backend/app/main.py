"""The ASGI application: middleware, routers, and nothing else."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="warchitecture API")

# The frontend is served from another origin (Static Web Apps) than the API
# (Container Apps), so every call from the browser is cross-origin and
# preflighted.
app.add_middleware(
    CORSMiddleware,
    # An allowlist read from CORS_ORIGINS. It takes no wildcards, so Static Web
    # Apps preview environments would each need adding, or allow_origin_regex.
    allow_origins=settings.cors_origins_list,
    # The token travels in an Authorization header, not a cookie, so the browser
    # never needs to attach credentials. Saying so here documents ADR-004 in
    # code, and sidesteps the footgun where allow_credentials=True combined with
    # a wildcard origin is silently ignored.
    allow_credentials=False,
    allow_methods=["*"],
    # Must cover Authorization, which the browser asks about during preflight.
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
