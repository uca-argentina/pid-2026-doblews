# Backend image for Azure Container Apps (ADR-008). Built from backend/ as the
# context, so the repo-root .env never reaches the image: every setting comes
# from the container's environment, as app/core/config.py expects in deploy.
FROM python:3.12-slim

# Pinned to the uv version the team uses locally, so uv.lock resolves the same.
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

# Compile .pyc at build time instead of on the first request after a cold
# start; copy instead of hardlink because the uv cache is not in the image; and
# use the base image's Python rather than letting uv download another one.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, in their own layer: a code-only change reuses it instead
# of reinstalling everything. --locked fails if uv.lock drifted from
# pyproject.toml, same as CI.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000

# Migrations run on every start. Safe only because the Container App is capped
# at one replica: two replicas booting together would race on alembic_version.
# A single uvicorn worker, because the replica has 0.5 GiB and each worker
# holds its own copy of the app and its connection pool.
# --proxy-headers: Container Apps terminates TLS at its ingress, so without it
# FastAPI believes every request is plain http and its redirects (a missing
# trailing slash) point to http:// URLs the browser blocks as mixed content.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips '*'"]
