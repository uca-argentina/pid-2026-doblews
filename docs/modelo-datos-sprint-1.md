# Modelo de datos — convenciones y estado

**Proyecto:** Proyecto Integral de Desarrollo — UCAio
**Base:** PostgreSQL 15+ / SQLAlchemy 2.0 / Alembic (ver [ADR-001](adr/0001-stack.md))
**Última revisión:** 2026-09-06

Este documento tiene dos funciones y ninguna más:

1. **Las convenciones de modelado** que aplican a toda tabla del proyecto, presente o futura.
2. **El estado del modelo**: qué está cerrado, dónde está definido, y qué sigue abierto.

**No** repite el modelo de usuarios, roles y permisos: eso está definido en [ADR-002](adr/0002-authorization-model.md) y esa ADR es la fuente de verdad. Si algo de acá la contradice, gana la ADR.

> **Nota histórica.** Hasta el 2026-09-06 este documento describía un modelo de un solo estudio, con roles globales `admin`/`arquitecto`/`cliente` y `obra.cliente_id`. ADR-002 lo reemplazó por un modelo multi-tenant con roles por ámbito. Los archivos que acompañaban a esa versión (`ddl-sprint-1.sql`, `models_sprint_1.py.reference`, `pruebas-invariantes.sql`) se eliminaron por describir el esquema viejo; están en el historial de git si hace falta consultarlos.

---

## 1. Criterio de diseño

Tres reglas ordenan todo lo que sigue. Si aparece una discusión de modelado, se resuelve volviendo acá.

1. **Se modela lo que las historias piden.** Una tabla vacía que nadie usa igual hay que mantenerla, migrarla y explicarla en la defensa.

2. **Salvo cuando agregarlo después sale caro.** Agregar una columna nullable es barato en cualquier momento. Partir una tabla en dos, o convertir una FK 1:N en N:M con datos cargados y código consultándola, es caro: migración de datos + reescritura de queries + retoque del front. Ese es el criterio por el que `estudio` entra desde la primera migración aunque al principio haya uno solo.

3. **La base defiende sus propios invariantes.** Todo lo que se pueda expresar como `NOT NULL`, `CHECK`, `UNIQUE` o `FOREIGN KEY` va en el esquema, no solamente en el validador de Pydantic. El backend no es el único que escribe en esa base: también lo hacen los seeds, las migraciones y ustedes mismos desde `psql` a las 2 de la mañana antes de la demo.

---

## 2. Estado del modelo

| Área | Estado | Dónde está definido |
|---|---|---|
| Estudios, usuarios, roles, permisos, asignaciones | **Cerrado** | [ADR-002](adr/0002-authorization-model.md) |
| `obra` (campos, `estudio_id`, membresía) | **Cerrado** | [ADR-002](adr/0002-authorization-model.md) §3 |
| `unidad_medida` | Cerrado en lo esencial | HU-0, §5 de este documento |
| `material` | **Abierto** — multi-tenant cambió el supuesto de catálogo global | §5 |
| `componente_constructivo` | **Abierto** — hay dos modelos en discusión | §5 |
| Presupuestos, planificación, proveedores | Fuera de alcance | — |

---

## 3. Convenciones de modelado

Aplican a toda tabla, incluidas las que todavía no existen.

### 3.1 Claves primarias: `BIGINT GENERATED ALWAYS AS IDENTITY`

Índices más chicos, URLs legibles (`/obras/12`), debug cómodo. `IDENTITY` en lugar de `SERIAL` porque es el estándar SQL y evita que alguien inserte un `id` a mano y desincronice la secuencia.

*Riesgo conocido:* los IDs son enumerables — cualquiera puede probar `/obras/13`. Se mitiga con el chequeo de acceso que ADR-002 exige, devolviendo **404 y no 403** para no revelar que el recurso existe. Ese chequeo hay que hacerlo igual con UUIDs; el UUID solo esconde el problema.

### 3.2 Multi-tenant: `estudio_id` en toda tabla de negocio

Toda tabla que contenga datos de un estudio lleva `estudio_id`, y **toda query de lectura filtra por él**. No es una convención cosmética: es lo único que impide que un estudio vea los datos de otro, y no lo garantiza el sistema de permisos (ver ADR-002 §8).

El filtro va en un repositorio base compartido, nunca repetido a mano en cada servicio.

### 3.3 Baja lógica con `is_active`

Dos consecuencias que hay que tener presentes desde el primer endpoint:

- Todo listado filtra `WHERE is_active = TRUE`. Conviene resolverlo en el mismo repositorio compartido que el `estudio_id` y no repetir el `where` en 20 lugares, porque el día que se olviden en uno solo aparece un material dado de baja en un desplegable.
- Las FKs **nunca** llevan `ON DELETE CASCADE` hacia datos de negocio, porque no borramos. El `CASCADE` se usa solo donde el borrado físico sí tiene sentido: vínculos puros como `rol_permiso`, no entidades.

Cuidado con el caso de los dos `is_active` con significados distintos, que ya aparece en el modelo: `usuario.is_active` es baja de la plataforma (no se loguea en ningún lado) y `usuario_estudio.is_active` es baja del padrón de un estudio (se loguea, pero ese estudio dejó de existir para esa persona).

### 3.4 Unicidad conviviendo con baja lógica

Hay una trampa clásica y se resuelve distinto según qué represente el campo:

- **Si el campo es una identidad, la unicidad es global**, incluyendo inactivos. Es el caso de `usuario.email`: si se permitiera reusar el email de alguien dado de baja, dos filas competirían por la misma credencial y el reingreso del usuario original sería ambiguo. Al reactivar, se reactiva la fila existente.
- **Si el campo es una etiqueta, la unicidad es parcial** (`... WHERE is_active`). Si dieron de baja "Cemento Loma Negra 50kg" por error y lo quieren volver a cargar, la base no tiene por qué impedirlo.

Ambos casos comparan en minúsculas (`lower(...)`) para que "Cemento" y "cemento" no convivan.

### 3.5 Dinero: `NUMERIC`, jamás `float`

`NUMERIC(14,2)` para importes. Un `float` acumula error de redondeo y en un presupuesto de obra eso se nota. En Python el tipo es `Decimal`; en el JSON de FastAPI se serializa como string o número según se configure Pydantic — definirlo una vez y que el front lo respete.

`moneda VARCHAR(3)` con código ISO 4217 y `CHECK` de tres mayúsculas, fijo en `'ARS'` por ahora. Está la columna, no está la lógica: no hay tabla de cotizaciones ni conversión. Cuando se necesite, el precio ya sabe en qué moneda está expresado y no hay que reinterpretar datos históricos.

### 3.6 Fechas: `TIMESTAMPTZ` para eventos, `DATE` para fechas de calendario

`created_at`, `updated_at`, `fecha_alta` son instantes → `TIMESTAMPTZ`. Nunca `TIMESTAMP` a secas: el día que el server esté en UTC y ustedes en UTC-3, los timestamps sin zona mienten.

`fecha_estimada_inicio` es una fecha de calendario → `DATE`. "La obra arranca el 15 de octubre" no tiene hora ni zona horaria.

### 3.7 Enumerados: `VARCHAR` + `CHECK`, no `ENUM` nativo

Un `CHECK` se modifica con un `ALTER TABLE` reversible; un tipo `ENUM` de Postgres no se puede alterar dentro de una transacción y complica el `downgrade` de Alembic.

La excepción son los enumerados que tienen datos propios o relaciones: esos son tablas. `rol` es tabla porque tiene nombre, descripción y una relación N:M con `permiso`; `unidad_medida` es tabla porque tiene abreviatura y magnitud.

### 3.8 FK compuesta para invariantes entre tablas

Es el truco más útil del modelo y ya se usa en dos lugares (ADR-002 §4 y §5). El patrón:

1. Declarar `UNIQUE (id, <discriminador>)` en la tabla destino — redundante con la PK a nivel lógico, necesario para que Postgres tenga a qué apuntar.
2. Hacer la FK de origen **compuesta**, incluyendo el discriminador.

Resultado: una regla que normalmente viviría en la capa de servicio pasa a ser imposible de violar, sin una línea de Python. Se usa para "un rol de obra no puede asignarse en el padrón de un estudio" y para "no podés meter en una obra a alguien que no está en el padrón de su estudio".

El costo es una columna redundante en la tabla de origen, que hay que setear al insertar. Vale la pena cuando la regla protege algo grave; no vale la pena para cualquier validación.

### 3.9 Nombres

- `snake_case`, tablas en **singular** (`usuario`, no `usuarios`), en español.
- Columnas técnicas de infraestructura en inglés (`is_active`, `created_at`) porque son parte del vocabulario del framework.
- FKs siempre `<tabla>_id`, PK siempre `id`.

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
| `estudio`, `usuario`, `rol`, `permiso`, `rol_permiso`, `usuario_plataforma`, `usuario_estudio`, `obra`, `obra_miembro` | [ADR-002](adr/0002-authorization-model.md) §3-§7 |
| El resto | Todavía no está definido — ver §5 |

El diagrama completo del modelo cerrado está en ADR-002 §3. `docs/diagrams/der.mmd` todavía refleja el modelo anterior y hay que actualizarlo.

---

## 5. Lo que queda abierto

### `unidad_medida` (HU-0)

Catálogo cerrado, global a la plataforma: un metro cuadrado es un metro cuadrado en todos los estudios. Se carga por seed, no por pantalla.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | `BIGINT` identity | |
| `codigo` | `VARCHAR(10)` | UNIQUE. `m2`, `m3`, `ml`, `u`, `kg`, `bolsa`, `lt` |
| `nombre` | `VARCHAR(60)` | "Metro cuadrado" |
| `abreviatura` | `VARCHAR(10)` | Lo que se muestra al lado del número: "m²" |
| `magnitud` | `VARCHAR(20)` | `superficie`, `volumen`, `longitud`, `masa`, `conteo`. No lo pide el sprint; entra porque el seed lo llena gratis y sin él, el día de las recetas, no hay forma de saber que convertir m² a bolsas necesita un factor y m² a m³ no tiene sentido |
| `is_active` | `BOOLEAN` | Permite retirar una unidad sin romper los registros que la usan |

**Lo único a confirmar:** que efectivamente sea global y no por estudio. Es lo razonable, pero hay que decirlo explícitamente.

### `material` (HU-4) — abierto

La decisión anterior era "catálogo global, no por obra". **Multi-tenant invalida ese supuesto**: los materiales y sobre todo sus precios son información sensible de cada estudio, y no pueden compartirse entre tenants.

Hay que decidir entre:

- **Catálogo por estudio** (`material.estudio_id`): lo más simple y lo más seguro. Cada estudio arranca vacío.
- **Semilla global + copia por estudio**: al crearse un estudio se le copia un catálogo base. Mejor experiencia inicial, más maquinaria.
- **Catálogo global compartido + precios por estudio**: dos tablas. Es el modelo correcto a largo plazo (habilita la normalización de catálogos de proveedores del Módulo 2), y el más caro ahora.

Las convenciones de §3 ya definen el resto: `NUMERIC(14,2)` con `CHECK >= 0`, `moneda` ISO, unicidad parcial del nombre entre activos, `precio_actualizado_en` como gancho de la futura tabla de histórico.

### `componente_constructivo` (HU-5) — abierto

Hay **dos modelos distintos** dando vueltas y hay que elegir uno:

- **Componente por obra, con jerarquía** (`obra_id`, `parent_id` self-referencial, `descripcion`, `medida`, `unidad_medida_id`). El componente es una línea del cómputo de esa obra. La FK compuesta de §3.8 garantiza que un componente y su padre son de la misma obra.
- **Componente como plantilla global + uso por obra** (`componente_constructivo` como catálogo tipo "Pared de 15cm" + `componente_material` como receta + `obra_componente` como cantidad usada en cada obra). Es lo que está hoy en `docs/diagrams/der.mmd`.

No son variantes del mismo modelo: son decisiones distintas sobre qué es un componente. La segunda adelanta parte del Módulo 2 (recetas constructivas). Hay que resolverlo antes de HU-5 y registrarlo como ADR.

---

## 6. Cómo se verifica

Con el repo ya montado, la verificación no es contra un DDL escrito a mano sino contra las migraciones, que son la fuente de verdad del esquema:

```bash
cd backend
uv run alembic downgrade base && uv run alembic upgrade head   # corre limpio sobre base vacía
uv run alembic check                                            # modelos y migraciones no divergieron
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
- [ ] Seeds: catálogo de `permiso`, `rol` y `rol_permiso` según ADR-002 §7; las 7 unidades de medida; el usuario de soporte inicial (con la contraseña fuera del repo, en `.env`).
- [ ] El trigger de `updated_at` está creado en la misma migración que las tablas.
- [ ] `alembic downgrade base` seguido de `alembic upgrade head` corre limpio sobre una base vacía. Probarlo el día 2, no el día 12.
- [ ] `docker compose up` levanta Postgres y las migraciones corren solas contra ese contenedor.
- [ ] Los tests de aislamiento existen antes del primer endpoint que lea datos de una obra, no después.
