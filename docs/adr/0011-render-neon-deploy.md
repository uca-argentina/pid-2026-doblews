# ADR-011: Deploy en Render y Neon

**Estado:** Propuesta
**Fecha:** 2026-11-05
**Contexto:** El ambiente de deploy de [ADR-008](0008-azure-deploy.md) se cayó al vencer la prueba de Azure. Esta ADR **reemplaza a ADR-008**.

## Contexto

[ADR-008](0008-azure-deploy.md) montó el ambiente en una Azure Free Account y dejó anotado que la prueba de 30 días vencía alrededor del 30/10/2026. Venció: la suscripción quedó `Disabled`, la API y el front dejaron de responder, y Azure avisó que borra los datos el 5/12/2026 si no se pasa a pago por uso.

Pasar a pago por uso habría mantenido el costo cerca de USD 0, porque los servicios de 12 meses y los cupos mensuales siguen. Pero **pago por uso no tiene tope de gasto**: el *spending limit* solo existe en ofertas con crédito. Un presupuesto de Azure avisa pero no corta, y armar un corte automático (alerta → runbook que apague todo) llega con horas de atraso y no garantiza cero. Además, la suscripción vive en el tenant de la UCA, y si la cuenta se desactiva al recibirse, quedarían recursos cobrándose a una tarjeta sin acceso al portal.

La restricción que había descartado a Render y Neon en ADR-008 ya no está: Mati liberó sus planes gratis. Esos planes no piden tarjeta y, si se pasa un límite, el servicio se suspende en vez de cobrar.

## Decisión

```
Browser ──► Render Static Site            frontend (build de Vite)
   └──────► Render Web Service (Free)     backend (Docker, buildeado por Render desde el repo)
                 │  sslmode=require
                 ▼
            Neon Postgres 16 (Free)
```

Toda la configuración de Render está versionada en **`render.yaml`** (Blueprint). Render lo lee de la rama que sigue el Blueprint, que es `main`.

### Backend: Render Web Service, plan Free

- **Runtime Docker con el mismo `backend/Dockerfile`**, con `rootDir: backend`. Render buildea la imagen desde el repo, así que ya no hace falta un registry: GHCR y su token de lectura se van.
- Región **Virginia**: Render no tiene región en Sudamérica, y Virginia está al lado del `us-east-1` de Neon. Importa más que la app y la base estén juntas que la distancia al navegador, porque cada request hace varias queries.
- **Las migraciones siguen corriendo al arrancar el contenedor.** Es seguro porque el plan Free corre una sola instancia, y es lo único posible porque el *pre-deploy command* de Render es solo para planes pagos.
- `healthCheckPath: /health`: Render no le pasa tráfico a un deploy nuevo hasta que responde. Una migración rota deja vivo el deploy anterior, que es lo mismo que daba el smoke test de `deploy.yml`.
- `--proxy-headers` sigue haciendo falta: Render también termina TLS en su proxy.
- Variables: `DATABASE_URL` se carga a mano en el dashboard (`sync: false`), `JWT_SECRET` lo genera Render (`generateValue`), y `CORS_ORIGINS` y `PORT=8000` están en el `render.yaml`.

### Base de datos: Neon, plan Free

- Postgres 16, como en `docker-compose.yml`, en AWS `us-east-1`.
- Se usa el endpoint **directo**, no el `-pooler`, para que Alembic no pase por PgBouncer. Con una sola instancia y un pool chico no hace falta un pooler.
- La URL es la de Neon con el esquema cambiado a `postgresql+psycopg://`, y conserva `sslmode=require`.
- Neon suspende la compute a los 5 minutos sin uso. `pool_pre_ping` en `app/db/session.py` evita que el primer request después de eso falle por una conexión muerta.

### Frontend: Render Static Site

- `npm ci && npm run build` desde `frontend/`, publicando `dist`. `VITE_API_URL` va en el `render.yaml` porque Vite la incrusta al buildear.
- Las reglas que estaban en `staticwebapp.config.json` pasan al `render.yaml`:
  - un rewrite `/*` → `/index.html` para que un F5 en una ruta de `BrowserRouter` no dé 404;
  - caché inmutable en `/assets/*` y `no-cache` en `/index.html`;
  - los dos headers de seguridad.
- Front y backend siguen en orígenes distintos (`warchitecture-web.onrender.com` y `warchitecture-api.onrender.com`), así que [ADR-004](0004-authentication.md) vale sin cambios.

### CD

- **Render deploya solo** cada push a `main`, con `autoDeployTrigger: checksPass`: espera a que pase `ci.yml` en ese commit. Se borra `.github/workflows/deploy.yml`.
- Con `rootDir` en cada servicio, un cambio solo en `frontend/` no redeploya el backend, ni al revés.

### Datos de demo

Igual que en ADR-008: las migraciones cargan permisos, unidades y catálogo del sistema, y las cuentas de demo se cargan una vez desde una máquina local con `app/db/seed_dev.py`, **con un `SEED_PASSWORD` propio del ambiente**. Los datos de Azure no se migraron: la base quedó inaccesible con la suscripción deshabilitada y solo tenía lo que genera ese seed.

## Costo

USD 0, garantizado: ninguno de los dos servicios tiene una tarjeta cargada. Los límites que importan:

| Recurso | Límite del plan gratis | Uso esperado |
|---|---|---|
| Render Web Service Free | 750 h/mes de instancia por workspace; 512 MB y 0,1 CPU; se duerme a los 15 min sin tráfico | Una sola instancia, que duerme casi todo el tiempo |
| Render Static Site | 100 GB/mes de ancho de banda | Muy por debajo |
| Neon Free | 0,5 GB de storage por proyecto; horas de compute mensuales limitadas, y se suspende sola sin uso | La base de demo pesa unos MB |

Si se pasa un límite, el servicio se suspende hasta el mes siguiente. No se cobra.

## Consecuencias

- **El ambiente sigue siendo `main`**, como en ADR-008, y el punto 4 de la Definition of Done se prueba acá.
- **Arranque en frío más lento.** Después de 15 minutos sin tráfico, el primer request tarda ≈ 30–60 s: Render levanta el contenedor, corre `alembic upgrade` y Neon despierta la compute. Con 0,1 CPU, bcrypt hace que cada login tarde unos segundos. Para una demo se abre `/health` unos minutos antes. En el plan Free no hay forma de dejar una instancia siempre prendida.
- **El backend y el front deployan en paralelo.** ADR-008 deployaba el front recién después del backend. Ahora, durante un par de minutos, un front nuevo puede llamar a un endpoint que todavía no está. Es aceptable para un ambiente de demo; si molesta, conviene mergear el cambio de backend en un PR anterior.
- **Sin smoke test propio.** Lo cubre `healthCheckPath`, pero solo valida que la app arranca, no un flujo. La verificación funcional sigue siendo manual (DoD punto 4).
- **Se van las fechas de ADR-008.** La del token de GHCR (31/12/2026) y la de los 12 meses de PostgreSQL (septiembre de 2027) ya no aplican. Tampoco queda nada atado a la cuenta de la UCA.
- **Azure queda vacío.** El resource group `rg-warchitecture`, el presupuesto y la suscripción se borran, y en GitHub se van los secrets de Azure, la variable `VITE_API_URL` y el paquete de GHCR.

## Alternativas descartadas

**Seguir en Azure pasando a pago por uso.** Costo esperado de USD 0 con la configuración de ADR-008, y sin migrar nada. Descartada porque no hay forma de garantizar ese cero: no existe un tope duro y el corte automático llega tarde. Además, la suscripción depende de una cuenta de la facultad que puede desaparecer.

**Pago por uso con corte automático (presupuesto → runbook que borra o apaga todo).** Reduce el riesgo, pero los datos de costo llegan con 8 a 24 h de atraso. También son piezas nuevas que mantener, y Azure vuelve a prender un PostgreSQL detenido a los 7 días.

**Render también para la base (Render Postgres Free).** Un solo proveedor y un solo dashboard. Descartada porque la base gratis de Render vence a los 30 días, antes de terminar la materia. Neon no vence.

**Vercel para el front, como decía ADR-001.** Tiene buenos previews por PR, pero agrega una cuenta, un `vercel.json` y un tercer dashboard. Render Static Site hace lo mismo para este caso y queda en el mismo `render.yaml`.

**Mantener `deploy.yml` llamando a deploy hooks de Render.** Conserva el orden backend → frontend y el smoke test, pero suma YAML y dos secrets más para algo que `checksPass` y `healthCheckPath` ya cubren casi entero.
