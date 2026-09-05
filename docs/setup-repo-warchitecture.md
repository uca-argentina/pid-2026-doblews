# Setup del repo — Proyecto Integral de Desarrollo

Runbook para ejecutar en WSL, en orden. Cada fase deja algo funcionando y commiteado.

**Convención:** el repo se llama `warchitecture` y vive en `~/warchitecture`. Cambiá el nombre si querés otro,
pero cambialo en todos lados.

**Cambio de alcance (2026-09-05):** arrancar features rápido pesa más que tener deploy temprano.
El runbook se divide en dos bloques: **Fases 0-10** te dejan codeando en local con todo lo que no
es diferible sin costo (Alembic, `.env` fuera de git, config por variables de entorno). **Fases 11-15**
son CI, Azure y CD — se ejecutan cuando el equipo tenga tiempo, no ahora. El orden entre esas cinco
está pensado para que cada una dependa solo de la anterior.

---

## Fase 0 — Cerrar decisiones (antes de tocar la terminal)

### 0.1 — Replanteo del modelo de datos (bloquea solo HU-5, no el arranque)

Quedó pendiente de confirmar el cambio pedido por la cátedra: `componente_constructivo` pasa a ser
catálogo global, con `componente_material` (receta) y `obra_componente` (uso en obra). Faltaba definir
si el total de materiales se persiste calculado o se computa on-the-fly, y el nombre final de la tabla
de uso.

Esto **no bloquea la Fase 8**: las tablas de HU-1 a HU-4 (`usuario`, `rol`, `usuario_rol`, `obra`,
`obra_miembro`, `material`) ya están cerradas y van en la primera migración. Los componentes entran
en una segunda migración cuando la cátedra confirme.

### 0.2 — Repo público o privado

Si el repo es **privado en plan Free**, la protección de rama (`main` protegida, PR obligatorio) puede
no estar disponible según tu plan. Dos salidas:

- Hacerlo **público**: es un proyecto de facultad, no hay secretos si `.env` nunca se commitea, y te
  habilita protecciones + minutos de Actions sin límite. Es lo que recomiendo.
- Dejarlo privado y sostener la regla por acuerdo del equipo (funciona con 3 personas, pero es honor system).

### 0.3 — Lo que queda explícitamente para el final

No se decide nada de esto ahora — queda documentado para no perderlo de vista:

- Azure (backend, frontend, base de datos) — Fase 12.
- La ADR que reemplaza la sección de hosting de la ADR-001 — se escribe recién en la Fase 12, no antes:
  para entonces ya hay código construido sobre el stack, así que el ritual de "ADR nueva que supersede
  a la vieja" tiene sentido real. Hoy, sin código de por medio, editarla en el lugar sería más simple
  pero prematuro — mejor ni tocarla todavía.
- La rama `dev` — Fase 14. Antes de que `main` dispare un deploy, `dev` es una rama que no hace nada.
- Los workflows de CI y de deploy — Fases 11, 13 y 14.

### 0.4 — Lo que no se difiere, aunque vayamos rápido

Cuatro cosas caras de retrofitear si se saltean ahora:

1. Alembic desde la primera migración (ya "no negociable" en ADR-001).
2. `.env` fuera de git desde el commit 1 — un secreto en el historial obliga a reescribir historia compartida.
3. Config por variables de entorno (`pydantic-settings`), no valores hardcodeados.
4. Frontend con un único cliente axios leyendo `import.meta.env.VITE_API_URL`, no la URL del back repetida
   por toda la app.

---

## Fase 1 — Prerrequisitos en WSL ✅ (hecho 2026-09-05)

Verificado en la distro donde vive `~/warchitecture`:

| Herramienta | Estado |
|---|---|
| git | 2.34.1 — ok |
| nvm / node | 0.40.1 / v24.19.0 — ok |
| python3 | 3.10.12 — no importa, `uv` gestiona su propio 3.12 en la Fase 5 |
| uv | 0.12.10 — ok |
| gh | reemplazado el paquete viejo de apt (2.4.0, 2022) por el oficial — logueado como `matifleman` |
| Claude Code | 2.1.261 — ok |
| Docker | pendiente — activar WSL Integration para esta distro en Docker Desktop (Settings → Resources → WSL Integration), después verificar `docker --version && docker compose version` |

`az` CLI no hace falta todavía — se instala en la Fase 12.

---

## Fase 2 — Esqueleto del repo y primer commit

`~/warchitecture` ya existe (es donde venís parado). Antes de nada, mirá qué tiene:

```bash
cd ~/warchitecture
ls -la
git status 2>/dev/null && echo "ya es un repo git" || echo "todavía no es un repo git"
```

- Si está vacía o solo tiene archivos sueltos que querés conservar: seguí abajo, `git init` no borra nada.
- Si `git status` dice que ya es un repo (por ejemplo si ya la inicializaste probando algo), avisame antes
  de correr `git init -b main` de nuevo — no pasa nada si la rama actual ya se llama `main`, pero si tiene
  otro nombre o ya hay commits de otra cosa, hay que decidir qué hacer con eso primero.

```bash
git init -b main

mkdir -p docs/adr docs/diagrams docs/historias \
         .claude/commands .claude/skills \
         backend frontend \
         .github/workflows
```

`.gitignore` en la raíz:

```bash
cat > .gitignore <<'EOF'
# Env
.env
.env.*
!.env.example

# Python
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/

# Node
node_modules/
dist/
.vite/

# Claude — config personal, no compartida
.claude/settings.local.json

# OS / editor
.DS_Store
.idea/
*.swp
EOF

git add . && git commit -m "chore: initial repo structure"
```

> `.claude/settings.json` **sí** se versiona (config del equipo).
> `.claude/settings.local.json` **no** (permisos y MCPs personales de cada uno).

---

## Fase 3 — Traer los docs desde OneDrive y reordenarlos

```bash
SRC="/mnt/c/Users/matuf/OneDrive - UCA/Documentos/UCA/5°Año Cuatrimestre 2/Proyecto Integral de Desarrollo"

cp "$SRC/docs/adr-001-stack.md"          docs/adr/0001-stack.md
cp "$SRC/docs/reglas-de-trabajo.md"      docs/
cp "$SRC/docs/historias-sprint-1.md"     docs/historias/sprint-1.md
cp "$SRC/docs/modelo-datos-sprint-1.md"  docs/
cp "$SRC/docs/ddl-sprint-1.sql"          docs/
cp "$SRC/docs/pruebas-invariantes.sql"   docs/
cp "$SRC/docs/models_sprint_1.py"        docs/models_sprint_1.py.reference
cp "$SRC/Claude outputs/der_v2.mmd"      docs/diagrams/der.mmd
cp "$SRC/Proyecto integral de desarrollo.docx" docs/propuesta-cliente.docx

git add docs && git commit -m "docs: import sprint 1 documentation from OneDrive"
```

Notas:

- Los PNG del DER **no** los traigas: `der.mmd` es la fuente, el PNG es derivado.
- `models_sprint_1.py` queda con sufijo `.reference` porque es el modelo **viejo** — material de
  consulta, no código vivo. Se borra cuando escribas los modelos reales en la Fase 8.
- El `.docx` es un binario en git. Para un archivo de la cátedra que casi no cambia, está bien.

Después de copiar, dejá la carpeta de OneDrive quieta: a partir de acá el repo es la fuente de verdad.

---

## Fase 4 — Capa Claude (CLAUDE.md, .claude/, .mcp.json)

Abrí Claude Code en la raíz del repo — ya tiene las ADRs y las reglas de trabajo, así que redacta
con contexto real en vez de con lo que le cuentes vos.

```bash
cd ~/warchitecture
claude
```

Prompt para pegar:

```
Leé docs/adr/0001-stack.md, docs/reglas-de-trabajo.md y docs/historias/sprint-1.md.

Con eso, generá:

1. CLAUDE.md en la raíz. Corto y operativo, no prosa larga. Que incluya:
   - qué es el proyecto en 2 líneas
   - stack, con link a docs/adr/0001-stack.md (no repitas el contenido)
   - cómo levantar el entorno local (docker compose up, migraciones)
   - convención de idioma: la conversación es en español; el código, los nombres de
     identificadores, los comentarios y los mensajes de commit son en inglés
   - convenciones no negociables, con link a docs/reglas-de-trabajo.md
   - una instrucción explícita: antes de proponer cualquier cambio de arquitectura o de
     modelo de datos, leer docs/adr/; toda decisión nueva se registra como ADR nueva,
     nunca editando una ADR aceptada

2. backend/CLAUDE.md y frontend/CLAUDE.md, cortos, solo con lo específico de cada stack.

3. docs/adr/template.md con el mismo formato que usa 0001-stack.md
   (Contexto / Decisión / Consecuencias / Alternativas descartadas).

4. .claude/settings.json versionable: permitir sin confirmación ruff, black, pytest,
   npm run build, npm run lint, alembic; pedir confirmación para git push y borrado de archivos.

5. .claude/commands/nueva-adr.md, nueva-historia.md y revisar-invariantes.md.

6. .mcp.json con un server de Postgres apuntando a la base local de docker compose,
   leyendo la connection string de una variable de entorno. Sin credenciales hardcodeadas.
```

```bash
git add . && git commit -m "chore: add Claude Code project configuration and ADR template"
```

---

## Fase 5 — Backend

```bash
cd ~/warchitecture/backend
uv init --bare

uv add fastapi "uvicorn[standard]" gunicorn sqlalchemy alembic \
       "psycopg[binary]" pydantic-settings pyjwt "passlib[bcrypt]" python-multipart
uv add --dev ruff black pytest pytest-asyncio httpx

mkdir -p app/{core,db,models,schemas,api/routes,services} tests
touch app/__init__.py app/main.py
```

Estructura objetivo:

```
backend/
├── app/
│   ├── main.py            # FastAPI app, routers, CORS
│   ├── core/
│   │   ├── config.py      # Settings con pydantic-settings
│   │   └── security.py    # hash de password, JWT
│   ├── db/
│   │   ├── session.py     # engine + SessionLocal
│   │   └── base.py        # DeclarativeBase
│   ├── models/            # SQLAlchemy 2.0
│   ├── schemas/           # Pydantic
│   ├── api/routes/        # un archivo por recurso
│   └── services/          # lógica que no va en el router
├── alembic/
├── tests/
└── pyproject.toml
```

Config de tooling en `backend/pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.black]
line-length = 100

[tool.pytest.ini_options]
pythonpath = ["."]
```

`main.py` mínimo — alcanza para arrancar, no hace falta tener features todavía:

```python
from fastapi import FastAPI

app = FastAPI(title="PID API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Alembic — esto sí es de la Fase 5, no se difiere:

```bash
uv run alembic init alembic
```

Editá `alembic/env.py` para que tome la URL de la variable de entorno y el metadata de tus modelos
(pedíselo a Claude Code: "configurá alembic/env.py para leer DATABASE_URL del entorno y usar el
metadata de app.db.base").

> No corras `alembic revision --autogenerate` todavía. Eso es la Fase 8.

```bash
cd ~/warchitecture && git add . && git commit -m "feat: scaffold FastAPI backend"
```

---

## Fase 6 — Frontend

```bash
cd ~/warchitecture
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Mantine
npm install @mantine/core @mantine/hooks @mantine/form @mantine/dates @mantine/notifications @mantine/charts dayjs
npm install -D postcss postcss-preset-mantine postcss-simple-vars

# Routing, data fetching
npm install react-router-dom axios @tanstack/react-query

# Formato
npm install -D prettier eslint-config-prettier
```

Mantine necesita `frontend/postcss.config.cjs`:

```js
module.exports = {
  plugins: {
    'postcss-preset-mantine': {},
    'postcss-simple-vars': {
      variables: {
        'mantine-breakpoint-xs': '36em',
        'mantine-breakpoint-sm': '48em',
        'mantine-breakpoint-md': '62em',
        'mantine-breakpoint-lg': '75em',
        'mantine-breakpoint-xl': '88em',
      },
    },
  },
};
```

En `src/main.tsx`: importar `@mantine/core/styles.css` y envolver la app en `<MantineProvider>`.

Creá ahora el cliente único de API (una de las 4 cosas de la Fase 0.4 que no se difieren) en
`src/lib/api.ts`:

```ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});
```

Y `frontend/.env.example`:

```bash
echo "VITE_API_URL=http://localhost:8000" > .env.example
```

Agregá a `frontend/package.json` un script `"format": "prettier --write ."`.

```bash
cd ~/warchitecture && git add . && git commit -m "feat: scaffold React frontend with Mantine"
```

---

## Fase 7 — Docker Compose + variables de entorno (local)

`docker-compose.yml` en la raíz — solo Postgres, backend y frontend corren nativos en WSL para hot
reload rápido:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: warchitecture
      POSTGRES_PASSWORD: warchitecture
      POSTGRES_DB: warchitecture
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U warchitecture"]
      interval: 5s
      retries: 5

volumes:
  pgdata:
```

`.env.example` del backend (versionado):

```bash
cat > .env.example <<'EOF'
DATABASE_URL=postgresql+psycopg://warchitecture:warchitecture@localhost:5432/warchitecture
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173
EOF

cp .env.example .env    # este no se commitea
docker compose up -d
```

```bash
git add . && git commit -m "chore: add docker compose and env template"
```

---

## Fase 8 — Modelos + primera migración

Escribí los modelos SQLAlchemy en `backend/app/models/` con lo que ya está cerrado: `usuario`, `rol`,
`usuario_rol`, `obra`, `obra_miembro`, `material`. `docs/models_sprint_1.py.reference` sirve de base.
Dejá afuera `componente_constructivo` y todo lo relacionado — eso espera a la Fase 0.1.

```bash
cd backend
uv run alembic revision --autogenerate -m "initial schema: users, roles, obras, materiales"
uv run alembic upgrade head
```

Verificá contra tus invariantes:

```bash
docker compose exec -T db psql -U warchitecture -d warchitecture < ../docs/pruebas-invariantes.sql
```

```bash
git add . && git commit -m "feat: add initial data model and migration"
```

Cuando la cátedra confirme el modelo de componentes: modelos nuevos → `alembic revision --autogenerate`
de nuevo → segunda migración. No se toca la primera.

---

## Fase 9 — Pre-commit

No es CI (no corre en GitHub, corre en tu máquina antes de cada commit), así que no hay motivo para
diferirlo — cierra el punto 4 de `reglas-de-trabajo.md` desde el primer commit compartido.

```bash
cd ~/warchitecture
uv tool install pre-commit

cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.4
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        files: ^frontend/
EOF

pre-commit install
pre-commit run --all-files
```

Revisá las versiones (`rev:`) con `pre-commit autoupdate`. Cada persona del equipo corre
`pre-commit install` una vez al clonar — ponelo en el `CLAUDE.md`.

```bash
git add . && git commit -m "chore: add pre-commit hooks"
```

---

## Fase 10 — GitHub (sin CI todavía)

```bash
cd ~/warchitecture
gh repo create <tu-usuario-o-org>/warchitecture --public --source=. --remote=origin --push
```

Protección básica de `main` (Settings → Branches → Add rule) — **sin** "require status checks"
todavía, porque no hay ningún workflow corriendo:

- Require a pull request before merging → 1 approval
- Do not allow bypassing the above settings

En Settings → General → Pull Requests, dejá activo solo **Allow squash merging**.

Agregá `.github/pull_request_template.md` con los tres campos de tus reglas: qué hace, qué HU/tarjeta
de Trello resuelve, cómo se probó.

```bash
git add . && git commit -m "chore: add PR template"
git push
```

---

### Acá arrancás con las features. Todo lo que sigue es CI/CD — cuando el equipo tenga tiempo.

---

## Fase 11 — CI (lint + build + tests, sin deploy)

Este es el primero de los cuatro pasos que quedaban pendientes, porque es el único que no depende de
Azure y el que hace que tu regla de "review cruzada obligatoria" sea real y no un acuerdo de palabra.

`.github/workflows/ci.yml` — pedíselo a Claude Code, que ya conoce el stack y las reglas de trabajo.
El contrato:

- Trigger: `pull_request` contra `main`. Nunca deploya.
- Job backend: `ruff check`, `black --check`, `pytest`, con un `services:` de Postgres para los tests
  que toquen la base.
- Job frontend: `npm ci`, `eslint`, `npm run build`.

```bash
cd ~/warchitecture && git add . && git commit -m "ci: add lint, build and test workflow"
git push
```

Hacé un PR de prueba, dejá que corra, y recién ahí volvé a Settings → Branches → editar la regla de
`main` y activá **Require status checks to pass** seleccionando ese workflow (aparece en la lista
solo después de correr al menos una vez).

---

## Fase 12 — Azure (provisioning)

Si tenés mail de UCA, fijate primero si calificás para **Azure for Students**: crédito inicial sin
tarjeta de crédito, que para este proyecto alcanza y sobra.

```bash
# az CLI, si todavía no lo instalaste en la Fase 1
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az version

az login
az account set --subscription "<subscription-id>"

LOC=eastus   # o brazilsouth si preferís menos latencia — comparar precios antes
RG=rg-warchitecture-prod

az group create -n $RG -l $LOC

# --- Postgres ---
az postgres flexible-server create \
  --resource-group $RG \
  --name pg-warchitecture-prod \
  --location $LOC \
  --tier Burstable --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 16 \
  --admin-user pidadmin \
  --admin-password '<password-fuerte>' \
  --public-access 0.0.0.0

az postgres flexible-server db create -g $RG -s pg-warchitecture-prod -d warchitecture

az postgres flexible-server firewall-rule create \
  -g $RG -n pg-warchitecture-prod --rule-name dev-mati \
  --start-ip-address <tu-ip> --end-ip-address <tu-ip>

# --- Backend: App Service ---
az appservice plan create -g $RG -n asp-warchitecture-prod --is-linux --sku B1
az webapp create -g $RG -p asp-warchitecture-prod -n app-warchitecture-api --runtime "PYTHON:3.12"

az webapp config set -g $RG -n app-warchitecture-api \
  --startup-file "alembic upgrade head && gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app"

az webapp config appsettings set -g $RG -n app-warchitecture-api --settings \
  DATABASE_URL="postgresql+psycopg://pidadmin:<password>@pg-warchitecture-prod.postgres.database.azure.com:5432/warchitecture?sslmode=require" \
  JWT_SECRET="<secret-fuerte>" \
  CORS_ORIGINS="https://<tu-swa>.azurestaticapps.net" \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Gotcha: App Service deshabilita credenciales básicas de SCM por defecto en apps nuevas.
# Sin esto, el deploy por publish profile falla con 401.
az resource update -g $RG \
  --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies \
  --name scm --parent sites/app-warchitecture-api --set properties.allow=true

# --- Frontend: Static Web Apps ---
az staticwebapp create -g $RG -n swa-warchitecture-web -l eastus2 --sku Free
```

Secrets para GitHub Actions:

```bash
az webapp deployment list-publishing-profiles \
  -g $RG -n app-warchitecture-api --xml > /tmp/pp.xml
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < /tmp/pp.xml && rm /tmp/pp.xml

az staticwebapp secrets list -n swa-warchitecture-web --query "properties.apiKey" -o tsv \
  | gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN
```

> Publish profile es el camino simple. OIDC con federated credentials (sin secretos de larga vida) es
> la práctica correcta — si sobra tiempo al final, migrar; no es lo que resta puntos en la materia.

Recién ahora, con código real construido sobre el stack, escribí la **ADR-0002** que reemplaza la
sección "Infraestructura y entorno" de la ADR-001 (Render/Railway + Vercel → Azure), y agregá en la
ADR-001 la línea `> Superseded en parte por ADR-0002 (hosting)`. Actualizá también
`docs/reglas-de-trabajo.md` §6 (Ambientes: Azure = demo, alimentada solo desde `main`, sin staging) y
§3 punto 4 del Definition of Done (pasa a "verificado en Azure post-merge", porque sin staging no se
puede verificar antes de mergear).

```bash
git add . && git commit -m "docs: add ADR-0002 (Azure hosting) and update team rules"
git push
```

---

## Fase 13 — Rama `dev`

Recién tiene sentido ahora, porque `main` está por empezar a disparar un deploy real:

```bash
git checkout -b dev
git push -u origin dev
```

En GitHub: cambiá la rama por defecto de los Pull Requests a `dev` (Settings → Branches → Default
branch, o simplemente indicándolo al abrir cada PR). Protegé `dev` igual que `main` (PR + 1 approval +
el mismo check de CI), pero sin gate de deploy — `dev` es donde se integra, `main` es lo que se publica.

La promoción `dev → main` va con **merge commit, no squash** (squash en ambos niveles hace divergir el
historial de las dos ramas).

---

## Fase 14 — CD (deploy en cada push a `main`)

Dos workflows más, cada uno con `paths:` filtrado para no redeployar lo que no cambió:

**`.github/workflows/deploy-api.yml`** — `on: push: branches: [main], paths: ['backend/**']`.
`azure/webapps-deploy@v3` con `AZURE_WEBAPP_PUBLISH_PROFILE`.

**`.github/workflows/deploy-web.yml`** — `on: push: branches: [main], paths: ['frontend/**']`.
`Azure/static-web-apps-deploy@v1` con `AZURE_STATIC_WEB_APPS_API_TOKEN`, `app_location: "frontend"`,
`output_location: "dist"`. `VITE_API_URL` tiene que estar en el `env` del step de **build**, porque
Vite la hornea en tiempo de compilación, no de runtime.

```bash
git add . && git commit -m "cd: add Azure deploy workflows for backend and frontend"
git push
```

Hacé un merge de prueba `dev → main` y confirmá que ambos deploys corren.

---

## Checklist de cierre (después de la Fase 14)

- [ ] `docker compose up -d && uv run uvicorn app.main:app --reload` levanta y `/health` responde
- [ ] `npm run dev` levanta el front y pega contra el back local
- [ ] `alembic upgrade head` corre limpio sobre una base vacía
- [ ] `pruebas-invariantes.sql` pasa
- [ ] Un PR de prueba dispara CI y no puede mergearse sin approval
- [ ] Un merge a `main` deploya solo, y `https://app-warchitecture-api.azurewebsites.net/health` responde
- [ ] El front en Azure carga y le pega al back de Azure (CORS configurado)
- [ ] `.env` no está en git: `git ls-files | grep -c '^\.env$'` devuelve `0`
- [ ] ADR-0002 (Azure) escrita, ADR-0001 marcada como superseded en parte
- [ ] `reglas-de-trabajo.md` actualizado (§6 ambientes, DoD punto 4)
- [ ] `dev` protegida igual que `main`, PRs targeteando `dev` por default

## Qué NO hacer, ni siquiera en la Fase 14

- Autenticación real (JWT completo con refresh, roles en el token) — es HU-1, no setup.
- Seeds de datos — cuando exista el modelo confirmado.
- Tests e2e con Playwright — después de tener pantallas.
- Todo lo que la ADR-001 marcó fuera de alcance: LLM, pgvector, base de grafos, importación de listas.

## Orden resumido

```
--- Para arrancar a codear ---
0.  Cerrar modelo (solo bloquea HU-5) + público/privado
1.  Prerrequisitos WSL (sin az CLI)
2.  git init + estructura + .gitignore
3.  Traer docs de OneDrive
4.  Claude Code genera CLAUDE.md / .claude / .mcp.json / template de ADR
5.  Backend scaffold + Alembic init (sin migración)
6.  Frontend scaffold + cliente axios único
7.  Docker Compose + .env (local)
8.  Modelos (HU-1 a HU-4) + primera migración
9.  Pre-commit
10. GitHub + protección básica de main (sin CI todavía)

--- CI/CD, cuando haya tiempo ---
11. CI (lint + build + test) + activar required status check
12. Azure provisioning + ADR-0002
13. Rama dev
14. CD (deploy-api.yml + deploy-web.yml)
```
