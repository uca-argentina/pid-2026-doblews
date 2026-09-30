# ADR-001: Stack tecnológico del proyecto

**Estado:** Aceptado
**Fecha:** 2026-09-03
**Contexto:** Materia Proyecto Integral de Desarrollo (UCAio) — plataforma web para arquitectos (cómputos, presupuestos, planificación de obras)

## Contexto

El documento de propuesta del cliente evalúa un abanico amplio de opciones (Next.js, .NET, Java/Spring, SQL Server, MySQL, Neo4j, Memgraph, ArangoDB, distintos LLMs, bases vectoriales). Ese análisis es válido para el proyecto completo a varios meses, pero el equipo es de 2-3 personas y el Sprint 1 dura 2 semanas con un alcance acotado (login, ABM de usuarios/obras/materiales, componentes constructivos). Se decidió cerrar un stack simple y productivo para el MVP, dejando explícitamente afuera lo que no se necesita todavía.

## Decisión

### Backend

- **Python + FastAPI**: framework asíncrono, documentación automática (Swagger), tipado con Pydantic.
- **SQLAlchemy 2.0** como ORM.
- **Alembic** para migraciones, desde la primera migración del proyecto (no negociable — evita reconstruir el esquema a mano más adelante).

### Base de datos

- **PostgreSQL**, sin bases adicionales por ahora.
- El camino crítico (CPM) del Módulo 3 se resuelve con un ordenamiento topológico sobre las tablas relacionales (`tarea` / `tarea_dependencia`), sin necesidad de una base de grafos para el volumen de tareas esperado en una obra.
- Se deja documentado que Neo4j/Memgraph quedan como opción a reevaluar únicamente si el cálculo de camino crítico sobre SQL se vuelve un cuello de botella real (no antes de tener el módulo de planificación funcionando).

### Frontend

- **React + TypeScript + Vite** (sin Next.js: no se necesita SSR y evita el costo de aprendizaje/configuración adicional del framework para el timeline del sprint).
- **Mantine** como librería de componentes UI — decisión tomada por: formularios con `@mantine/form` (el sprint 1 tiene 4 ABMs completos), componentes ya resueltos para lo que viene pronto (`DatePicker`, `Modal`, `Notifications`, `Table`), sistema de grillas responsive nativo, y `@mantine/charts` disponible para cuando se implemente el módulo de cashflow, todo bajo el mismo sistema de diseño.
- Alternativa evaluada y descartada por ahora: **shadcn/ui** — mejor si el objetivo fuera un diseño 100% de marca, pero implica más setup inicial (Tailwind, capa de formularios propia) que no se justifica en el Sprint 1.

### Infraestructura y entorno

- **Docker Compose** con Postgres para desarrollo local, evita diferencias de entorno entre los miembros del equipo.
- **Deploy**: backend + base de datos en Render o Railway, frontend en Vercel. Deploy funcionando desde los primeros días del sprint, no reservado para el final.

  > **Reemplazado por [ADR-008](0008-azure-deploy.md) (2026-09-30).** El deploy es en Azure: backend en Container Apps, base en PostgreSQL Flexible Server y frontend en Static Web Apps. Los planes gratis de Render y Neon ya estaban ocupados por otros proyectos del equipo. El resto de esta sección sigue vigente.
- **CI**: GitHub Actions con lint (`ruff` + `eslint`) y verificación de build en cada Pull Request.

## Fuera de alcance (explícitamente, para este momento del proyecto)

- Integración de LLM para unificación semántica de catálogos de proveedores (Módulo 2).
- Base de datos vectorial (pgvector u otra).
- Base de datos de grafos (Neo4j/Memgraph/ArangoDB).
- Importación masiva de listas de precios (CSV/Excel).
- Cualquier funcionalidad de los Módulos 2, 3 y 4 del documento de propuesta que no esté en las historias del Sprint 1.

Estos puntos no están descartados del proyecto — están fuera del alcance actual y se reevalúan cuando el sprint correspondiente los requiera.

## Consecuencias

- El equipo puede arrancar a codear el día 2 sin bloquearse en evaluaciones de tecnología.
- El modelo de datos en PostgreSQL debe diseñarse pensando en los módulos futuros (por ejemplo, `parent_id` nullable en `componente_constructivo` para la EDT jerárquica) para no requerir migraciones destructivas más adelante.
- Si el volumen de tareas o la complejidad del grafo de dependencias crece mucho, la decisión de no usar una base de grafos se revisita puntualmente en ese momento, con datos reales del proyecto.
