# backend/CLAUDE.md

FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL. Ver [../docs/adr/0001-stack.md](../docs/adr/0001-stack.md) para el porqué.

## Modelo de datos

Antes de tocar modelos o migraciones, leer:
- [../docs/modelo-datos-sprint-1.md](../docs/modelo-datos-sprint-1.md)
- [../docs/ddl-sprint-1.sql](../docs/ddl-sprint-1.sql)
- [../docs/models_sprint_1.py.reference](../docs/models_sprint_1.py.reference)

Toda regla que se pueda expresar en el esquema (`NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`) va en el esquema, no solo en Pydantic.

## Reglas del proyecto

- Toda migración de esquema pasa por Alembic, desde la primera. Nunca alterar tablas a mano.
- ABM = baja lógica (`is_active`), nunca `DELETE` físico.
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
