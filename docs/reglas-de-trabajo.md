# Reglas de trabajo del equipo — Proyecto Integral de Desarrollo

**Equipo:** 2-3 personas (fullstack)
**Herramientas:** GitHub (código) + Trello (tareas)

Este documento fija cómo trabajamos como equipo durante todo el proyecto. No es negociable en cada sprint — se define una vez acá y se revisa solo si algo deja de funcionar en la práctica.

---

## 1. Gestión de tareas (Trello)

- Un board único para el proyecto, con listas: `Backlog` → `To Do (sprint actual)` → `En progreso` → `Review/QA` → `Done`.
- Una tarjeta por historia de usuario, nombrada igual que en el documento de historias (`HU-1: Iniciar sesión`), para que coincida con ramas y commits.
- Cada tarjeta lleva: descripción (Como/quiero/para), checklist con los criterios de aceptación, responsable asignado, fecha límite.
- **Regla de oro:** nadie mueve una tarjeta a `Done` sin que su PR esté mergeado a `main`. `Review/QA` es donde vive mientras el PR está abierto.
- Al cierre de cada sprint, `Done` se archiva y se arranca lista limpia — no se acumulan tarjetas viejas en el board activo.

## 2. Control de versiones (Git/GitHub)

**Branching**

- `main` = lo que está (o va a estar) hosteado. `dev` = rama de integración, donde se juntan las historias antes de promocionar a `main`. Ambas protegidas: nadie pushea directo a ninguna de las dos, solo se llega por Pull Request aprobado.
- Una rama por historia/tarea, creada desde `dev`: `feat/hu1-login`, `fix/hu3-validacion-fecha`, `chore/setup-docker`. El PR de esa rama apunta a `dev`, no a `main`.
- Ramas cortas: se abren, se trabajan 1-3 días y se mergean. Si una rama vive más de una semana, es señal de que la tarea estaba mal cortada.
- Antes de abrir el PR, traer los cambios de `dev` (`rebase` o `merge`) para no descubrir conflictos recién en el review.
- Promoción `dev → main`: PR aparte, con **merge commit, no squash** (squash en ambos niveles hace divergir el historial de las dos ramas). Se hace cuando el equipo decide que lo acumulado en `dev` está listo para quedar hosteado, no automáticamente en cada historia.

**Commits**

- Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- Mensaje en modo imperativo y en español o inglés, pero consistente para todo el equipo (definir uno y no mezclar).
- Commits chicos y frecuentes. Un commit = un cambio lógico, no "checkpoint del día".

**Pull Requests**

- Descripción mínima: qué hace, qué historia/tarjeta de Trello resuelve (link), cómo se probó.
- **Al menos 1 review cruzada antes de mergear** (con 2-3 personas, no hace falta más de 1 aprobación).
- El que abre el PR no se autoaprueba ni mergea su propio código sin el visto bueno del otro.
- PRs chicos (idealmente bajo ~400 líneas de diff). Un PR gigante nadie lo revisa en serio.
- Squash merge a `main` para mantener el historial limpio — el detalle de commits intermedios queda en la rama.

## 3. Definition of Done

Una historia está "terminada" solo si se cumplen **todas** estas condiciones:

1. Código mergeado a `main` (no en una rama, no "casi listo").
2. Migración de base de datos aplicada y versionada (si corresponde).
3. Cumple **todos** los criterios de aceptación de la tarjeta/historia — verificados a mano, no de memoria.
4. Probado en el ambiente de deploy (Render/Vercel), no solo en localhost.
5. Sin errores de lint ni de build.
6. Responsive verificado en un ancho mobile (375px) si la historia toca UI.

Si falta cualquiera de estos puntos, la tarjeta se queda en `Review/QA`, no pasa a `Done`.

## 4. Estilo de código

- Comentarios de código en inglés; nombres de variables/funciones en inglés.
- Backend: `ruff` (lint) + `black` (format) antes de cada commit.
- Frontend: `eslint` + `prettier` antes de cada commit.
- Si se puede, hook de pre-commit local para que esto sea automático y no dependa de acordarse.

## 5. Comunicación y ritmo

- Un canal de chat único del equipo (WhatsApp/Discord) para coordinación rápida — decisiones de peso quedan en Trello o en un commit/PR, no solo en el chat (se pierden).
- Check-in corto al principio de cada bloque de trabajo: qué hago hoy, qué bloqueo tengo. No hace falta reunión formal con 2-3 personas; alcanza con un mensaje.
- Bloqueos se avisan apenas aparecen, no se acumulan hasta el día de entrega.
- Cualquier decisión que cambie el alcance de una historia (agregar/sacar un criterio de aceptación) se discute entre todos antes de implementarla, y se refleja en el documento de historias.

## 6. Ambientes

- `.env.example` versionado en el repo; `.env` real nunca se commitea.
- Cada uno corre el proyecto local con Docker Compose (Postgres incluido) para evitar el "en mi máquina anda".
- El ambiente de deploy (staging) se mantiene siempre actualizado con `main` — es lo que se muestra en la demo, no localhost.

---

*Última actualización: acordado por el equipo al inicio del Sprint 1. Se revisa si alguna regla deja de ser práctica, no antes.*
