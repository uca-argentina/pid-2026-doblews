# Modelo de datos — convenciones y estado

**Proyecto:** Proyecto Integral de Desarrollo — UCAio
**Base:** PostgreSQL 15+ / SQLAlchemy 2.0 / Alembic (ver [ADR-001](adr/0001-stack.md))
**Última revisión:** 2026-10-07

Este documento tiene dos funciones y ninguna más:

1. **Las convenciones de modelado** que aplican a toda tabla del proyecto, presente o futura.
2. **El estado del modelo**: qué está cerrado, dónde está definido, y qué sigue abierto.

El dibujo del esquema no está acá: es [der.md](der.md), que se genera desde los modelos.

**No** repite el modelo de usuarios, roles y permisos: eso está definido en [ADR-002](adr/0002-authorization-model.md) y esa ADR es la fuente de verdad. Si algo de acá la contradice, gana la ADR.

> **Nota histórica.** Hasta el 2026-09-06 este documento describía un modelo de un solo estudio, con roles globales `admin`/`architect`/`client` y `project.client_id`. ADR-002 lo reemplazó por un modelo multi-tenant con roles por ámbito. Los archivos que acompañaban a esa versión (`ddl-sprint-1.sql`, `models_sprint_1.py.reference`, `pruebas-invariantes.sql`) se eliminaron por describir el esquema viejo; están en el historial de git si hace falta consultarlos.

---

## 1. Criterio de diseño

Tres reglas ordenan todo lo que sigue. Si aparece una discusión de modelado, se resuelve volviendo acá.

1. **Se modela lo que las historias piden.** Una tabla vacía que nadie usa igual hay que mantenerla, migrarla y explicarla en la defensa.

2. **Salvo cuando agregarlo después sale caro.** Agregar una columna nullable es barato en cualquier momento. Partir una tabla en dos, o convertir una FK 1:N en N:M con datos cargados y código consultándola, es caro: migración de datos + reescritura de queries + retoque del front. Ese es el criterio por el que `firm` entra desde la primera migración aunque al principio haya uno solo.

3. **La base defiende sus propios invariantes.** Todo lo que se pueda expresar como `NOT NULL`, `CHECK`, `UNIQUE` o `FOREIGN KEY` va en el esquema, no solamente en el validador de Pydantic. El backend no es el único que escribe en esa base: también lo hacen los seeds, las migraciones y ustedes mismos desde `psql` a las 2 de la mañana antes de la demo.

---

## 2. Estado del modelo

| Área | Estado | Dónde está definido |
|---|---|---|
| Estudios, usuarios, roles, permisos, asignaciones | **Cerrado** | [ADR-002](adr/0002-authorization-model.md) |
| `project` (campos, `firm_id`, membresía) | **Cerrado** | [ADR-002](adr/0002-authorization-model.md) §3 |
| `unit_of_measure` | **Cerrado** | [ADR-003](adr/0003-recipe-catalog.md) |
| `resource` (antes `material`) | **Cerrado** | [ADR-003](adr/0003-recipe-catalog.md) |
| `recipe`, `recipe_resource`, `project_recipe` (antes `building_component`) | **Cerrado** | [ADR-003](adr/0003-recipe-catalog.md) |
| Recetas del estudio (`recipe.firm_id`) | **Cerrado** | [ADR-006](adr/0006-firm-recipes.md) |
| Versiones del presupuesto (`budget_version`, `budget_version_item`, `budget_version_line`) | **Cerrado** | [ADR-007](adr/0007-budget-versions.md) |
| Planificación (rubros, tareas, dependencias, avance) | Sprint 3, en definición | [sprint-3.md](historias/sprint-3.md) |
| Proveedores y listas de precios | Sprint 3, en definición | [sprint-3.md](historias/sprint-3.md) |

---

## 3. Convenciones de modelado

Aplican a toda tabla, incluidas las que todavía no existen.

### 3.1 Claves primarias: `BIGINT GENERATED ALWAYS AS IDENTITY`

Índices más chicos, URLs legibles (`/projects/12`), debug cómodo. `IDENTITY` en lugar de `SERIAL` porque es el estándar SQL y evita que alguien inserte un `id` a mano y desincronice la secuencia.

*Riesgo conocido:* los IDs son enumerables — cualquiera puede probar `/projects/13`. Se mitiga con el chequeo de acceso que ADR-002 exige, devolviendo **404 y no 403** para no revelar que el recurso existe. Ese chequeo hay que hacerlo igual con UUIDs; el UUID solo esconde el problema.

### 3.2 Multi-tenant: `firm_id` en toda tabla de negocio

Toda tabla que contenga datos de un estudio lleva `firm_id`, y **toda query de lectura filtra por él**. No es una convención cosmética: es lo único que impide que un estudio vea los datos de otro, y no lo garantiza el sistema de permisos (ver ADR-002 §8).

El filtro va en un repositorio base compartido, nunca repetido a mano en cada servicio.

### 3.3 Baja lógica con `is_active`

Dos consecuencias que hay que tener presentes desde el primer endpoint:

- Todo listado filtra `WHERE is_active = TRUE`. Conviene resolverlo en el mismo repositorio compartido que el `firm_id` y no repetir el `where` en 20 lugares, porque el día que se olviden en uno solo aparece un material dado de baja en un desplegable.
- Las FKs **nunca** llevan `ON DELETE CASCADE` hacia datos de negocio, porque no borramos. El `CASCADE` se usa solo donde el borrado físico sí tiene sentido: vínculos puros como `role_permission`, no entidades.

Cuidado con el caso de los dos `is_active` con significados distintos, que ya aparece en el modelo: `account.is_active` es baja de la plataforma (no se loguea en ningún lado) y `firm_member.is_active` es baja del padrón de un estudio (se loguea, pero ese estudio dejó de existir para esa persona).

### 3.4 Unicidad conviviendo con baja lógica

Hay una trampa clásica y se resuelve distinto según qué represente el campo:

- **Si el campo es una identidad, la unicidad es global**, incluyendo inactivos. Es el caso de `account.email`: si se permitiera reusar el email de alguien dado de baja, dos filas competirían por la misma credencial y el reingreso del usuario original sería ambiguo. Al reactivar, se reactiva la fila existente.
- **Si el campo es una etiqueta, la unicidad es parcial** (`... WHERE is_active`). Si dieron de baja "Cemento Loma Negra 50kg" por error y lo quieren volver a cargar, la base no tiene por qué impedirlo.

Ambos casos comparan en minúsculas (`lower(...)`) para que "Cemento" y "cemento" no convivan.

### 3.5 Dinero: `NUMERIC`, jamás `float`

`NUMERIC(14,2)` para importes. Un `float` acumula error de redondeo y en un presupuesto de obra eso se nota. En Python el tipo es `Decimal`; en el JSON de FastAPI se serializa como string o número según se configure Pydantic — definirlo una vez y que el front lo respete.

`currency VARCHAR(3)` con código ISO 4217 y `CHECK` de tres mayúsculas, fijo en `'ARS'` por ahora. Está la columna, no está la lógica: no hay tabla de cotizaciones ni conversión. Cuando se necesite, el precio ya sabe en qué moneda está expresado y no hay que reinterpretar datos históricos.

### 3.6 Fechas: `TIMESTAMPTZ` para eventos, `DATE` para fechas de calendario

`created_at`, `updated_at`, `joined_at` son instantes → `TIMESTAMPTZ`. Nunca `TIMESTAMP` a secas: el día que el server esté en UTC y ustedes en UTC-3, los timestamps sin zona mienten.

`estimated_start_date` es una fecha de calendario → `DATE`. "La obra arranca el 15 de octubre" no tiene hora ni zona horaria.

### 3.7 Enumerados: `VARCHAR` + `CHECK`, no `ENUM` nativo

Un `CHECK` se modifica con un `ALTER TABLE` reversible; un tipo `ENUM` de Postgres no se puede alterar dentro de una transacción y complica el `downgrade` de Alembic.

La excepción son los enumerados que tienen datos propios o relaciones: esos son tablas. `role` es tabla porque tiene nombre, descripción y una relación N:M con `permission`; `unit_of_measure` es tabla porque tiene abreviatura y magnitud.

### 3.8 FK compuesta para invariantes entre tablas

Es el truco más útil del modelo y ya se usa en dos lugares (ADR-002 §4 y §5). El patrón:

1. Declarar `UNIQUE (id, <discriminador>)` en la tabla destino — redundante con la PK a nivel lógico, necesario para que Postgres tenga a qué apuntar.
2. Hacer la FK de origen **compuesta**, incluyendo el discriminador.

Resultado: una regla que normalmente viviría en la capa de servicio pasa a ser imposible de violar, sin una línea de Python. Se usa para "un rol de obra no puede asignarse en el padrón de un estudio" y para "no podés meter en una obra a alguien que no está en el padrón de su estudio".

El costo es una columna redundante en la tabla de origen, que hay que setear al insertar. Vale la pena cuando la regla protege algo grave; no vale la pena para cualquier validación.

### 3.9 Nombres

- **Todo identificador va en inglés**: tablas, columnas, clases, códigos de permisos y de roles, y los valores de enumerados que el código compara (`scope`, `code`). La documentación y la conversación del equipo siguen en español; el código no.
- `snake_case`, tablas en **singular** (`account`, no `accounts`).
- FKs siempre `<tabla>_id`, PK siempre `id`.

Hasta el 2026-09-07 esta sección decía "tablas en español, columnas técnicas en inglés". Se cambió por dos razones. La primera es que contradecía a `CLAUDE.md`, que ya pedía identificadores en inglés. La segunda es que la frontera "dominio vs. infraestructura" no existe en la práctica: obligaba a decidir columna por columna de qué lado caía cada una —`fecha_alta` es dominio o es auditoría?— y ya había producido `es_sistema` conviviendo con `is_active`. Ver [ADR-002 §3](adr/0002-authorization-model.md).

Un caso vale la pena recordarlo: **`usuario` se traduce como `account`, no como `user`**, porque `user` es palabra reservada en PostgreSQL y obligaría a entrecomillarla en toda query cruda.

### 3.10 Constraints con nombre explícito

Prefijos `pk_`, `fk_`, `uq_`, `ck_`, `ix_`. Nunca dejar que Postgres los nombre solo.

En SQLAlchemy esto se configura una vez con `naming_convention` en el `MetaData`, y **tiene que estar antes de la primera migración autogenerada**: si no, Alembic no puede referenciar constraints anónimas para modificarlas después.

### 3.11 `updated_at` lo mantiene un trigger

Un trigger de Postgres (`BEFORE UPDATE ... EXECUTE FUNCTION set_updated_at()`), no el ORM. Así vale también para los `UPDATE` hechos a mano o desde una migración. La función se crea en la misma migración que las tablas.

### 3.12 Migraciones: esquema y datos, separadas

Una migración que crea el esquema, y otra distinta con los datos semilla. Separarlas permite recrear el esquema sin arrastrar seeds y hace obvio en el historial qué cambió estructura y qué cambió datos.

---

## 4. Dónde está definida cada tabla

No duplicamos diccionarios de datos: cada tabla se define en un solo lugar.

| Tablas | Fuente |
|---|---|
| `firm`, `account`, `role`, `permission`, `role_permission`, `platform_member`, `firm_member`, `project`, `project_member` | [ADR-002](adr/0002-authorization-model.md) §3-§7 |
| `unit_of_measure`, `resource`, `recipe`, `recipe_resource`, `project_recipe` | [ADR-003](adr/0003-recipe-catalog.md) §2 |
| `recipe.firm_id` | [ADR-006](adr/0006-firm-recipes.md) |
| `budget_version`, `budget_version_item`, `budget_version_line` | [ADR-007](adr/0007-budget-versions.md) |
| El resto | Todavía no está definido — ver §5 |

**El diagrama del esquema completo es [der.md](der.md), y se genera**: sale de los modelos de SQLAlchemy con `uv run python -m scripts.generate_erd`, y el CI falla si no coincide con ellos. Muestra el estado actual, tabla por tabla, con sus `CHECK` y sus claves compuestas.

El reparto es este: **`der.md` dice qué hay, las ADR dicen por qué.** Los diagramas dentro de ADR-002 §3 y ADR-003 §2 quedan como ilustración de cada decisión en el momento en que se tomó, y si difieren de `der.md` gana `der.md`. Una ADR que propone tablas nuevas las dibuja ella; pasan a `der.md` solas cuando existe el modelo.

Hasta el 2026-10-07 no había diagrama global: `docs/diagrams/der.mmd` se había eliminado porque reflejaba el modelo anterior a multi-tenant. Lo que cambió no es la disciplina del equipo sino que ya no se escribe a mano.

---

## 5. Lo que queda abierto

**Nada del Sprint 1.** Las tres entradas que vivían acá —`unit_of_measure`, `material` y `building_component`— se cerraron en [ADR-003](adr/0003-recipe-catalog.md), que también renombró dos de ellas:

| Lo que decía este documento | Cómo quedó |
|---|---|
| `unit_of_measure`, con la duda de si era global o por estudio | **Global a la plataforma**, sembrada. Un metro cuadrado es un metro cuadrado en todos los estudios |
| `material`, con tres opciones sobre a quién pertenece | **`resource`**, del sistema, con una columna `type` (`material` / `labor` / `equipment`) que permite que una receta futura incluya mano de obra y equipo sin tablas nuevas |
| `building_component`, con dos modelos incompatibles en discusión | **`recipe`** + **`recipe_resource`** (el catálogo: qué lleva 1 unidad) y **`project_recipe`** (la obra: cuánta cantidad). Sin composición recursiva |

El Sprint 2 cerró tres de los pendientes que quedaban anotados: las recetas propias de cada estudio ([ADR-006](adr/0006-firm-recipes.md)), la mano de obra y el equipo sembrados (T-06) y el precio congelado en un presupuesto cerrado ([ADR-007](adr/0007-budget-versions.md)).

**Abierto para el Sprint 3**, todavía sin ADR: rubros y tareas de la obra, dependencias entre tareas, avance, y proveedores con sus listas de precios. Las preguntas de diseño están listadas en [sprint-3.md](historias/sprint-3.md).

Sigue abierto y sin fecha: precios por estudio, histórico de precios y composición de recetas. ADR-003 §Consecuencias lista cada uno con la condición bajo la cual se revisa.

---

## 6. Cómo se verifica

Con el repo ya montado, la verificación no es contra un DDL escrito a mano sino contra las migraciones, que son la fuente de verdad del esquema:

```bash
cd backend
uv run alembic downgrade base && uv run alembic upgrade head   # corre limpio sobre base vacía
uv run alembic check                                            # modelos y migraciones no divergieron
uv run python -m scripts.generate_erd --check                   # der.md coincide con los modelos
uv run pytest                                                   # invariantes y aislamiento
```

Los tests de `pytest` cubren tres familias, y las tres son obligatorias:

1. **Invariantes del esquema**: por cada regla que la base debe defender, un test que intenta violarla y espera que la base la rechace (email duplicado con otra capitalización, precio negativo, medida cero, rol de ámbito equivocado en una tabla de asignación, miembro de obra que no está en el padrón del estudio).
2. **Aislamiento entre estudios**: por cada endpoint, un intento de acceso con un usuario de otro estudio, esperando 404. Conviene parametrizarlo sobre la tabla de rutas de FastAPI para que un endpoint nuevo quede cubierto solo.
3. **Seed del catálogo de permisos**: que el conjunto de permisos de cada rol coincida con la tabla de ADR-002 §7.

---

## 7. Checklist antes de escribir la primera migración

- [ ] `naming_convention` configurada en el `MetaData` **antes** del primer `alembic revision --autogenerate`.
- [ ] Una migración de esquema + una migración de seeds, separadas.
- [ ] Seeds: catálogo de `permission`, `role` y `role_permission` según ADR-002 §7; las 7 unidades de medida; el usuario de soporte inicial (con la contraseña fuera del repo, en `.env`).
- [ ] El trigger de `updated_at` está creado en la misma migración que las tablas.
- [ ] `alembic downgrade base` seguido de `alembic upgrade head` corre limpio sobre una base vacía. Probarlo el día 2, no el día 12.
- [ ] `docker compose up` levanta Postgres y las migraciones corren solas contra ese contenedor.
- [ ] Los tests de aislamiento existen antes del primer endpoint que lea datos de una obra, no después.
