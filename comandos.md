# Comandos de Warchitecture: qué hace cada uno, dónde correrlo y cuándo

**Antes de correr cualquiera, mirá el prompt de la terminal: ¿estás en la carpeta correcta?**
Dejá **dos terminales fijas**: una en `backend/` y otra en `frontend/` (más una tercera para git/servidores si hace falta).

| Carpeta | Para qué |
|---|---|
| raíz del repo | git, `grep`, `docker compose` |
| `backend/` | todo lo que empieza con `uv run` |
| `frontend/` | todo lo que empieza con `npm` / `npx` |

---

## 1. Arrancar el entorno (al empezar a trabajar)

| Comando | Dónde | Cuándo |
|---|---|---|
| `docker compose up -d` | raíz | Para levantar Postgres. Si `docker` no está en el PATH pero el backend conecta, Postgres ya está corriendo |
| `uv run uvicorn app.main:app --reload` | `backend/` | Levantar la API en `:8000`. `--reload` la reinicia sola al guardar. Swagger en `http://localhost:8000/docs` |
| `npm run dev` | `frontend/` | Levantar la UI en `:5173`. **Si cambiás `.env`, reiniciarlo** (Vite solo lo lee al arrancar) |
| `cp .env.example .env` | raíz y `frontend/` | Una sola vez en un clon nuevo (los `.env` no se versionan) |
| `uv sync` | `backend/` | Instalar dependencias de Python (clon nuevo o si cambió `pyproject.toml`) |
| `npm install` | `frontend/` | Instalar dependencias de JS |
| `uv run python -m app.db.seed_dev` | `backend/` | Cargar datos de ejemplo. Cuentas: `ana@estudionorte.test` (owner), `alba@...` (architect), `carla@...` (client), `bruno@estudiosur.test` (otra firma). Contraseña: `warchitecture` |

**Si algo no arranca:**

| Síntoma | Comando para diagnosticar |
|---|---|
| `Address already in use` | `lsof -nP -iTCP:8000 -sTCP:LISTEN` (o `:5173`) → ver el PID |
| ¿Es mío ese proceso? | `lsof -a -p <PID> -d cwd` → mira la carpeta desde donde corre |
| Pararlo | `kill <PID>` |
| Front: "No pudimos conectar con el servidor" | falta `frontend/.env` con `VITE_API_URL=http://localhost:8000`; reiniciar `npm run dev` |
| `Failed to spawn: uvicorn` | estás en la carpeta equivocada (falta `backend/`) |

---

## 2. Git (al empezar, durante y al cerrar)

| Comando | Cuándo |
|---|---|
| `git branch --show-current` | Saber en qué rama estás (hacelo siempre antes de empezar) |
| `git status -sb` | Ver qué archivos cambiaron y cuáles son nuevos |
| `git switch -c practice/nombre main` | Crear rama nueva **desde main** y pararte en ella |
| `git diff main --stat` | Resumen: qué archivos cambiaste respecto a main |
| `git diff main` | El detalle línea por línea (útil para revisar antes de commitear) |
| `git add -A && git commit -m "feat(x): ..."` | Guardar tu trabajo |
| `git commit --amend -m "..."` / `--no-edit` | Corregir el último commit (**solo si no hiciste push**) |
| `git checkout -- <archivo>` | Deshacer cambios de un archivo (vuelve a como estaba en el último commit) |
| `git log --oneline -3` | Ver los últimos commits |
| `bash reset-practice.sh nombre` | Rama limpia desde main + base de práctica reseteada (solo en el clon de práctica) |

**Mensajes de commit** (en inglés, Conventional Commits): `feat:` algo nuevo · `fix:` arreglo · `refactor:` · `chore:` · `docs:` · `test:`. Ejemplo: `feat(suppliers): add optional website field`.

---

## 3. Buscar en el código (el comando más útil del parcial)

| Comando | Cuándo |
|---|---|
| `grep -rn "texto" backend/app` | Encontrar todos los lugares donde aparece algo. Salida: `archivo:línea:texto` |
| `grep -rn "address" backend/app frontend/src` | **"Seguir las huellas"** de un campo/feature parecida: la lista es tu checklist de cambios |
| `grep -n "@router" backend/app/api/routes/x.py` | Ver todas las rutas de un archivo con su número de línea |
| `grep -rn "Materiales" frontend/src` | Encontrar un componente buscando un texto que ves en pantalla |

⚠️ No todo resultado del `grep` es relevante (ej. `address` también aparece en obras, usuarios, etc.). Revisá el archivo antes de tocar.

---

## 4. Backend (en `backend/`)

### Base de datos y migraciones
Usarlo **cada vez que cambiás un modelo** (`backend/app/models/`).

| Comando | Cuándo |
|---|---|
| `uv run alembic revision --autogenerate -m "mensaje"` | Generar la migración **después** de cambiar el modelo. Si dice que no detecta cambios, probablemente no tocaste el modelo |
| *(abrir y leer el archivo generado)* | Siempre: debe tener solo lo tuyo. Borrá los comentarios `# ### commands auto generated ###` |
| `uv run alembic upgrade head` | Aplicar las migraciones pendientes a la base |
| `uv run alembic check` | Verificar que modelos y migraciones coinciden. Tiene que decir `No new upgrade operations detected` |
| `uv run alembic downgrade -1 && uv run alembic upgrade head` | Probar que la migración se puede deshacer y rehacer (el proyecto lo exige) |
| `uv run alembic heads` | Ver la última revisión (la necesitás como `down_revision` en una migración escrita a mano, ej. seed de permisos) |
| `uv run python -m scripts.generate_erd` | Regenerar `docs/der.md` **después de tocar un modelo** (el CI falla si está desactualizado) |

### Tests, formato y lint
| Comando | Cuándo |
|---|---|
| `uv run pytest` | Correr todos los tests (cerrando el trabajo) |
| `uv run pytest tests/test_suppliers_api.py` | Un solo archivo (mientras desarrollás) |
| `uv run pytest -k "nombre" -x` | Solo los tests que matchean el nombre, y parar en el primer fallo |
| `uv run black .` | Formatear todo el código Python |
| `uv run ruff check . --fix` | Lint (+ arregla lo simple, como imports desordenados) |
| `uv run black --check .` | Solo verifica el formato sin modificar (como lo hace el CI) |

---

## 5. Frontend (en `frontend/`)

| Comando | Cuándo |
|---|---|
| `npx prettier --write src` | Formatear. **Siempre antes de commitear** (si no, el pre-commit lo rechaza) |
| `npm run lint` | ESLint: errores y malas prácticas |
| `npx tsc -b` | Solo chequeo de tipos de TypeScript (rápido) |
| `npm run build` | Chequeo de tipos + build completo. Es lo que corre el CI |

---

## 6. Recetas: "cambié X, ¿qué corro?"

**Cambié un modelo / agregué una columna o tabla:**
```
(backend)  alembic revision --autogenerate  →  leer el archivo  →  alembic upgrade head
           →  alembic check  →  downgrade -1 && upgrade head  →  generate_erd  →  pytest
```

**Cambié solo código de backend (rutas, servicios, schemas):**
```
(backend)  probar en /docs  →  pytest  →  black .  →  ruff check . --fix
```

**Cambié solo código de frontend:**
```
(frontend)  probar en el navegador (desktop y 375 px)  →  prettier --write src  →  npm run lint  →  npm run build
```

**Voy a entregar / commitear (cierre de trabajo, en este orden):**
1. `uv run black . && uv run ruff check . --fix` (backend)
2. `npx prettier --write src && npm run lint && npm run build` (frontend)
3. `uv run pytest` (backend)
4. `uv run alembic check` y `uv run python -m scripts.generate_erd` (si tocaste modelos)
5. Probar el flujo completo en la UI, en desktop y en 375 px
6. `git status -sb` (¿está todo lo que tiene que estar? ¿hay archivos de más?) y `git diff main --stat`
7. `git add -A && git commit -m "feat(...): ..."`

---

## 7. Errores que ya nos pasaron

| Error | Causa | Solución |
|---|---|---|
| `No Python files are present` / `Failed to spawn` | Comando de `uv` corrido desde `frontend/` o la raíz | Pararse en `backend/` |
| `ruff check` dice "All checks passed" pero no revisó nada | Idem | Pararse en `backend/` |
| `No module named 'scripts'` | Idem | Pararse en `backend/` |
| La UI no conecta con la API | Falta `frontend/.env` | `cp .env.example .env` y reiniciar `npm run dev` |
| `Address already in use` | Quedó un servidor viejo corriendo | `lsof ...` → `kill <PID>` |
| `autogenerate` no detecta cambios | No modificaste el modelo (`models/x.py`) | Agregar la columna al modelo primero |
| Backend 500 `AttributeError` / `UndefinedColumn` | Modelo cambiado pero migración sin aplicar | `alembic upgrade head` |
| Seed falla después de editarlo | Se tocó un `address=` que era de otra entidad (ej. obra) | Revertir: `git checkout -- backend/app/db/seed_dev.py` |
| Ruta nueva responde 422 en lugar de datos | Está declarada después de una ruta con parámetro (`/{id}`) | Declararla **antes** de la ruta dinámica |
| Prettier falla en CI/pre-commit | No formateaste | `npx prettier --write src` |
| Filtro funciona en desktop pero no en mobile | Se usó la lista original en el `.map` de las tarjetas | Buscar con `grep` todos los usos de la variable |
