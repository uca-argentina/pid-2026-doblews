---
description: Verificar que el esquema de base de datos sigue cumpliendo los invariantes del modelo de datos
---

Contexto: el modelo de datos (`docs/modelo-datos-sprint-1.md`) establece que la base defiende sus propios invariantes (`NOT NULL`, `CHECK`, `UNIQUE`, `FOREIGN KEY`), no solo el validador de Pydantic.

1. Leer `docs/modelo-datos-sprint-1.md` y `docs/ddl-sprint-1.sql` para tener la lista completa de invariantes esperados.
2. Correr `docs/pruebas-invariantes.sql` contra la base local (la de `docker compose`) y reportar qué pruebas pasan y cuáles fallan.
3. Si algún invariante del documento no está reflejado en las migraciones de Alembic actuales, señalarlo — no corregirlo automáticamente sin confirmación, porque puede implicar una migración destructiva.
4. Si se agregó una tabla o columna nueva desde la última revisión, señalar qué invariantes le faltarían (baja lógica `is_active`, `NOT NULL` en campos obligatorios, `FOREIGN KEY` correspondiente) según las reglas de `docs/modelo-datos-sprint-1.md`.
