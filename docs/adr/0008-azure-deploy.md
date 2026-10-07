# ADR-008: Deploy en Azure — Container Apps, Static Web Apps y PostgreSQL Flexible Server

**Estado:** Aceptada
**Fecha:** 2026-09-30
**Contexto:** T-07 (deploy y promoción `dev → main`), arrastrada del Sprint 1. Reemplaza la parte "Deploy" de [ADR-001](0001-stack.md) (Render/Railway + Vercel).

## Contexto

[ADR-001](0001-stack.md) decidió deployar el backend y la base en Render o Railway y el frontend en Vercel, "funcionando desde los primeros días del sprint". Eso nunca se hizo: el CI corre lint, migraciones, tests y build, pero no deploya, y sin ambiente de deploy **ninguna historia cumple el punto 4 de la Definition of Done** ([reglas-de-trabajo §3](../reglas-de-trabajo.md)). La demo se mostraba desde localhost.

Al retomarlo cambiaron dos restricciones:

- **Render y Neon ya están ocupados.** El equipo tiene otros proyectos corriendo en sus planes gratis, que son por cuenta.
- **El presupuesto es USD 0.** Es un proyecto de materia hasta diciembre de 2026, sin cliente que pague la infraestructura.

La cuenta usada es una **Azure Free Account** (oferta `FreeTrial`): USD 200 por 30 días, más servicios "12 meses gratis" y cupos mensuales que no vencen. Azure for Students fue rechazada. La suscripción quedó en el directorio (tenant) de la UCA, porque la cuenta se creó con el mail de la facultad, y ese directorio **no permite crear app registrations**.

El código ya estaba preparado para un deploy en contenedores: `app/core/config.py` lee variables de entorno reales cuando no hay `.env`, `main.py` expone `/health` y toma los orígenes de CORS de `CORS_ORIGINS`, `session.py` usa `pool_pre_ping`, y el frontend lee `VITE_API_URL` al buildear.

## Decisión

Todo en un resource group, `rg-warchitecture`, en **Brazil South**, la región más cercana con PostgreSQL B1ms y Container Apps disponibles. La Static Web App se registra en East US 2 porque no existe en Brazil South, pero se sirve desde una red global y la región solo guarda sus metadatos.

```
Browser ──► Static Web Apps (Free)          frontend (build de Vite)
   └──────► Container Apps (Consumption)    backend (imagen privada en GHCR)
                 │  sslmode=require
                 ▼
            PostgreSQL Flexible Server B1ms
```

### Backend: Azure Container Apps

- Imagen Docker construida con `backend/Dockerfile`: `python:3.12-slim` y `uv` con la versión fijada, `uv sync --locked --no-dev`, usuario no-root.
- **0,25 vCPU / 0,5 GiB, mínimo 0 y máximo 1 réplica, un solo worker de uvicorn.** Con 0,5 GiB no entran dos workers.
- `--proxy-headers`: el ingress de Container Apps termina TLS. Sin ese flag, FastAPI arma las redirecciones con `http://` y el navegador las bloquea por contenido mixto.
- **Las migraciones corren al arrancar el contenedor** (`alembic upgrade head && uvicorn …`). Es correcto solo porque el máximo es una réplica: dos arrancando a la vez competirían por `alembic_version`. Si alguna vez se escala, se pasan a un Container Apps Job que corra antes del deploy.
- `DATABASE_URL`, `JWT_SECRET` y el token de GHCR viven como *secrets* de la Container App. `CORS_ORIGINS` es una variable común con la URL de la Static Web App.

### Base de datos: PostgreSQL Flexible Server

- **Burstable B1ms, 32 GB, sin storage autogrow, sin alta disponibilidad, backup local de 7 días**, versión 16 como en `docker-compose.yml`. Es exactamente la configuración que cubre la oferta de 12 meses. Cualquiera de esas opciones encendida se cobra.
- Acceso público con firewall: solo la regla "Allow Azure services" (0.0.0.0). Para operar desde una máquina local, se agrega su IP y se quita al terminar.

### Frontend: Azure Static Web Apps, plan Free

- `frontend/public/staticwebapp.config.json`:
  - un `navigationFallback` a `/index.html`, porque la app usa `BrowserRouter` y sin él un F5 en una ruta interna da 404;
  - caché inmutable para `/assets/*`;
  - dos headers de seguridad básicos.
- Front y backend quedan en **orígenes distintos** (`*.azurestaticapps.net` y `*.azurecontainerapps.io`), igual que con Vercel y Render. El razonamiento de [ADR-004](0004-authentication.md), que usa un token en el header `Authorization` y no cookies cross-site, sigue valiendo sin cambios.

### Imagen: GitHub Container Registry, privada

- La imagen es privada porque el repo lo es, y una imagen pública expone el código del backend. Un paquete de GHCR que se hace público no puede volver a ser privado.
- GHCR da 500 MB gratis para paquetes privados, y la imagen pesa ~108 MB comprimida. El workflow de deploy **conserva solo las dos últimas versiones**: la que corre y la anterior, para volver atrás.
- La Container App baja la imagen con un token clásico que solo tiene `read:packages` y vence el 31/12/2026.

### CD: `.github/workflows/deploy.yml`

- Corre con cada push a `main` y a mano con `workflow_dispatch`. No repite lint ni tests: nada llega a `main` sin un PR que pasó `ci.yml`.
- **Login a Azure con OIDC contra una managed identity** (`id-gh-deploy`) con una federated credential para `repo:matifleman/warchitecture:ref:refs/heads/main`. Se usa en lugar de un service principal porque el tenant de la UCA no deja crear app registrations. La identidad tiene rol Contributor solo sobre `rg-warchitecture`, y en GitHub no queda ninguna contraseña de Azure.
- **Job backend:**
  1. Build y push de la imagen, con tag igual al SHA del commit (nunca `latest`).
  2. `az containerapp update --image`.
  3. Smoke test contra `/health`: el `update` termina antes de que la app responda, y una migración que falla solo se ve ahí.
  4. Borrado de las versiones viejas de la imagen.
- **Job frontend:** corre después del backend, así un front que llama a un endpoint nuevo nunca sale antes que el endpoint. Buildea con `VITE_API_URL` (variable del repo) y sube `frontend/dist`.

### Datos de demo

El ambiente recibe por migración solo lo que va a toda base: permisos, unidades y catálogo del sistema. Las cuentas de demo se cargan con `app/db/seed_dev.py`, corrido una vez desde una máquina local, **con un `SEED_PASSWORD` propio del ambiente**. La contraseña de desarrollo está en `.env.example` y en el código, y la URL del ambiente es pública.

## Costo

Precios de la API pública de Azure (`prices.azure.com`, Brazil South, septiembre de 2026), calculados con un mes de 2.592.000 s:

| Recurso | Qué da gratis la oferta | Costo con esta configuración |
|---|---|---|
| PostgreSQL B1ms + 32 GB | 750 h/mes (un servidor prendido todo el mes) por 12 meses | USD 0. Sin la oferta serían ≈ USD 16/mes |
| Container Apps | 180.000 vCPU-s + 360.000 GiB-s + 2M requests por mes, sin vencimiento | USD 0 con mínimo 0 réplicas: alcanza para ≈ 200 h/mes de réplica corriendo a 0,25 vCPU / 0,5 GiB |
| Static Web Apps Free | 100 GB/mes de tráfico, sin vencimiento | USD 0 |
| Log Analytics | 5 GB/mes; el workspace tiene un tope de 0,1 GB/día | USD 0 |
| GHCR | 500 MB privados | USD 0 conservando dos versiones |

Dejar una réplica prendida todo el mes (mínimo 1) costaría ≈ USD 4 si pasa casi todo el tiempo sin atender requests. Por eso el mínimo es 0 y se sube a 1 solo en los días de demo: un día son ≈ 21.600 vCPU-s, dentro del cupo gratis.

Una alerta de presupuesto de USD 1 por mes (`budget-usd1`, a nivel suscripción) avisa si algo empieza a cobrar. Avisa, pero no corta el gasto.

## Consecuencias

- Las historias pueden cumplir el punto 4 de la Definition of Done, y la demo se muestra desde el ambiente de deploy.
- **El ambiente es `main`.** Lo que se mergea a `main` se deploya solo, y lo que está en `dev` no llega al ambiente hasta la promoción.
- **Arranque en frío.** Con mínimo 0, el primer request después de unos minutos sin tráfico tarda ≈ 15 s, porque arranca el contenedor y corre `alembic upgrade`. Cada login tarda ≈ 2 s porque bcrypt corre sobre 0,25 vCPU. Para una demo se sube el mínimo a 1 y después se vuelve a 0: `az containerapp update -g rg-warchitecture -n ca-warchitecture-api --min-replicas 1`.
- **Una migración rota deja el deploy en rojo, no el ambiente caído.** La revisión nueva no arranca y el smoke test falla. Se corrige con un commit nuevo a `main`, o apuntando la Container App a la imagen anterior, que el workflow conserva.
- **Hay fechas que vigilar:**
  - **~30/10/2026:** vence la prueba de 30 días. Hay que pasar la suscripción a pago por uso, o Azure la deshabilita y el ambiente se cae. Los servicios de 12 meses siguen gratis después del cambio, pero desaparece el tope de gasto de la prueba.
  - **31/12/2026:** vence el token de GHCR que usa la Container App para bajar la imagen.
  - **Septiembre de 2027:** terminan los 12 meses gratis de PostgreSQL.
- La suscripción depende de la cuenta de la facultad. Si la UCA desactiva la cuenta, por ejemplo al recibirse, se pierde el acceso. Aceptable para un proyecto que termina en diciembre.
- Los secretos del ambiente (contraseña de Postgres, `JWT_SECRET`, `SEED_PASSWORD`, token de la Static Web App) no viven en el repo: están en la Container App, en los secrets de GitHub y en el gestor de contraseñas del equipo.

## Alternativas descartadas

**Render + Neon (lo que decía ADR-001, con Neon en lugar del Postgres de Render).** Era lo más simple: deploy directo desde el repo sin escribir un workflow. Descartada porque los planes gratis de las dos ya están ocupados por otros proyectos del equipo. Además, el Postgres gratis de Render vence a los 90 días.

**Azure App Service (B1 o F1) para el backend.** Deploya código Python sin Dockerfile, pero su build (Oryx) no entiende `uv`, y habría que mantener un `requirements.txt` sincronizado a mano con `uv.lock`. B1 cuesta ≈ USD 13/mes fijos. F1 es gratis pero tiene 60 minutos de CPU por día y se descarga a los 20 minutos sin uso, con arranques de ≈ 30 s. Container Apps queda en USD 0, corre la misma imagen que se prueba localmente y deja abierto Container Apps Jobs para las migraciones si alguna vez hace falta.

**Azure Container Registry en lugar de GHCR.** Está integrado con Container Apps y no necesita un token para bajar la imagen, pero el plan Basic cuesta ≈ USD 5/mes y no entra en ninguna oferta gratis.

**Imagen pública en GHCR.** Elimina el límite de 500 MB y el token de lectura. Descartada porque publica el código del backend de un repo privado, y porque no tiene vuelta atrás.

**Service principal con OIDC para GitHub Actions.** Es la forma más documentada, pero el tenant de la UCA no deja crear app registrations. La managed identity con federated credential da lo mismo sin tocar el directorio.

**Crear la cuenta con un mail personal para tener un tenant propio.** Evitaría depender de la UCA, pero Microsoft da una Free Account por persona, identificada por tarjeta y teléfono. Una segunda cuenta probablemente quedaría como pago por uso sin los servicios de 12 meses, y PostgreSQL pasaría a costar ≈ USD 16/mes.
