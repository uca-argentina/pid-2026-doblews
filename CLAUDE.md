# CLAUDE.md

Plataforma web para arquitectos: cómputos, presupuestos y planificación de obras. Proyecto de la materia Proyecto Integral de Desarrollo (UCAio).

## Stack

Ver [docs/adr/0001-stack.md](docs/adr/0001-stack.md) (ADR-001, Aceptada). No lo repitas de memoria — leelo.

## Entorno local

Setup inicial al clonar (una sola vez):

```bash
cp .env.example .env          # nunca commitear .env
pre-commit install            # hooks de ruff/prettier antes de cada commit
```

Para levantar todo:

```bash
docker compose up -d          # levanta Postgres
cd backend && uv sync         # instala deps del backend
uv run alembic upgrade head   # aplica migraciones
cd ../frontend && npm install # instala deps del frontend
```

`.env.example` está versionado; copiarlo a `.env` (nunca commitear `.env`).

## Ambiente de deploy

Azure, deployado desde `main` por `.github/workflows/deploy.yml`. Ver [docs/adr/0008-azure-deploy.md](docs/adr/0008-azure-deploy.md).

- Frontend: https://orange-mushroom-009669d0f.6.azurestaticapps.net
- API: https://ca-warchitecture-api.delightfuldune-fd794876.brazilsouth.azurecontainerapps.io (`/docs` para Swagger)
- El primer request después de unos minutos sin tráfico tarda ~15 s (escala a cero). Para una demo: `az containerapp update -g rg-warchitecture -n ca-warchitecture-api --min-replicas 1`, y volver a `0` después.
- Las cuentas demo usan un `SEED_PASSWORD` propio del ambiente, no el de `.env.example`.

## Idioma

- Conversación con el usuario: **español**.
- Código, nombres de identificadores, comentarios y mensajes de commit: **inglés** (Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).

## Convenciones del equipo

No negociables, ver [docs/reglas-de-trabajo.md](docs/reglas-de-trabajo.md): branching, PRs, Definition of Done, baja lógica en vez de `DELETE`, `ruff`/`black` en backend, `eslint`/`prettier` en frontend.

## Arquitectura y modelo de datos

Antes de proponer cualquier cambio de arquitectura o de modelo de datos: **leer `docs/adr/` primero**.

Toda decisión nueva se registra como una ADR nueva (usar [docs/adr/template.md](docs/adr/template.md)). **Las ADR se editan**: el proyecto está en desarrollo y una decisión se afina mientras se implementa. Si lo que cambia es el fondo —se decide otra cosa, no se precisa lo mismo— conviene escribir una ADR nueva que la reemplace, para no perder por qué se había decidido lo anterior.

## Subdirectorios

- [backend/CLAUDE.md](backend/CLAUDE.md)
- [frontend/CLAUDE.md](frontend/CLAUDE.md)
