---
description: Verificar que el esquema de base de datos sigue cumpliendo los invariantes del modelo de datos
---

Contexto: el modelo de datos establece que **la base defiende sus propios invariantes** (`NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`), no solo el validador de Pydantic. La fuente de verdad del esquema son las migraciones de Alembic; no hay un DDL de referencia paralelo.

1. Leer para tener la lista completa de invariantes esperados:
   - `docs/adr/0002-authorization-model.md` — `firm`, `account`, `role`, `permission`, `project` y las reglas que la base **no** puede garantizar (§11).
   - `docs/modelo-datos-sprint-1.md` — convenciones de modelado (§3) y qué sigue abierto (§5).
2. Con la base de `docker compose` levantada, correr desde `backend/`:
   - `uv run alembic upgrade head` — las migraciones aplican limpio.
   - `uv run alembic check` — modelos y migraciones no divergieron.
   - `uv run pytest` — reportar qué pasa y qué falla.
3. Contrastar el esquema real contra los invariantes del documento y señalar los que **no** estén reflejados en las migraciones actuales. No corregirlos automáticamente sin confirmación: puede implicar una migración destructiva.
4. Verificar específicamente las tres familias de tests que el modelo exige, y señalar si alguna falta:
   - **Invariantes del esquema**: por cada regla, un test que intenta violarla y espera que la base la rechace.
   - **Aislamiento entre estudios**: por cada endpoint, un acceso con usuario de otro estudio esperando 404. Debe estar parametrizado sobre la tabla de rutas de FastAPI, no escrito a mano uno por uno.
   - **Seed de permisos**: el conjunto de permisos de cada rol coincide con la tabla de ADR-002 §7.
5. Si se agregó una tabla o columna nueva desde la última revisión, señalar qué le faltaría según las convenciones: `firm_id` si es una tabla de negocio, baja lógica `is_active`, `NOT NULL` en los campos obligatorios, la `FOREIGN KEY` correspondiente, y el trigger de `updated_at`.
