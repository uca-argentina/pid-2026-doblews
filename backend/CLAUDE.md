# backend/CLAUDE.md

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL. Ver [../docs/adr/0001-stack.md](../docs/adr/0001-stack.md) para el porqué.

## Modelo de datos

Antes de tocar modelos o migraciones, leer:
- [../docs/adr/0002-authorization-model.md](../docs/adr/0002-authorization-model.md) — estudios, usuarios, roles, permisos y `obra`. Es la fuente de verdad de esas tablas.
- [../docs/modelo-datos-sprint-1.md](../docs/modelo-datos-sprint-1.md) — convenciones de modelado y qué sigue abierto.

Toda regla que se pueda expresar en el esquema (`NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`) va en el esquema, no solo en Pydantic.

El esquema real lo define **Alembic**: no hay un DDL de referencia paralelo. Para verificar que modelos y migraciones no divergieron, `alembic check`.

## Reglas del proyecto

- Toda migración de esquema pasa por Alembic, desde la primera. Nunca alterar tablas a mano.
- ABM = baja lógica (`is_active`), nunca `DELETE` físico.
- Multi-tenant: toda tabla de negocio lleva `estudio_id` y **toda lectura filtra por él**, desde el repositorio base. Recurso ajeno → 404, nunca 403.
- Autorización: los endpoints chequean **permisos** (`obra.editar`), nunca roles (`if rol == "arquitecto"`). Endpoint sin permiso declarado no responde.
- Contraseñas hasheadas (bcrypt/argon2), nunca texto plano.
- Precios: `Numeric`/`Decimal`, nunca `float`.
- `ruff` (lint) + `black` (format) antes de cada commit.

## Comandos

```bash
ruff check .
black .
pytest
alembic revision --autogenerate -m "..."
alembic upgrade head
```
