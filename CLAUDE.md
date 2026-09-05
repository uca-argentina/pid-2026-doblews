# CLAUDE.md

Plataforma web para arquitectos: cómputos, presupuestos y planificación de obras. Proyecto de la materia Proyecto Integral de Desarrollo (UCAio).

## Stack

Ver [docs/adr/0001-stack.md](docs/adr/0001-stack.md) (ADR-001, Aceptada). No lo repitas de memoria — leelo.

## Entorno local

```bash
docker compose up -d          # levanta Postgres (y demás servicios definidos en compose)
cd backend
alembic upgrade head           # aplica migraciones
```

`.env.example` está versionado; copiarlo a `.env` (nunca commitear `.env`).

## Idioma

- Conversación con el usuario: **español**.
- Código, nombres de identificadores, comentarios y mensajes de commit: **inglés** (Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`).

## Convenciones del equipo

No negociables, ver [docs/reglas-de-trabajo.md](docs/reglas-de-trabajo.md): branching, PRs, Definition of Done, baja lógica en vez de `DELETE`, `ruff`/`black` en backend, `eslint`/`prettier` en frontend.

## Arquitectura y modelo de datos

Antes de proponer cualquier cambio de arquitectura o de modelo de datos: **leer `docs/adr/` primero**.

Toda decisión nueva se registra como una ADR nueva (usar [docs/adr/template.md](docs/adr/template.md)). Una ADR aceptada **no se edita** — si cambia, se supersede con una ADR nueva que lo diga explícitamente.

## Subdirectorios

- [backend/CLAUDE.md](backend/CLAUDE.md)
- [frontend/CLAUDE.md](frontend/CLAUDE.md)
