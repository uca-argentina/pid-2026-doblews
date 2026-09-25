# ADR-007: Versiones del presupuesto

**Estado:** Propuesta
**Fecha:** 2026-09-25
**Contexto:** Modelo de datos para congelar el presupuesto de una obra en versiones inmutables. Desbloquea HU-12 del Sprint 2 y resuelve dos pendientes que dejaron anotados ADR-003 y ADR-005.

---

## Contexto

### Qué quedó pendiente, en las dos ADR que esta resuelve

[ADR-005 §7](0005-catalog-administration.md), sobre el precio vivo del cómputo:

> Congelar el precio en la línea de cómputo | Un estudio necesite presupuestos estables para presentarle a su cliente

[ADR-003 §Consecuencias](0003-recipe-catalog.md), sobre que la obra referencia el catálogo y no lo copia:

> Copia de la receta hacia la obra | Existan presupuestos cerrados que no deban cambiar retroactivamente

Las dos ADR anotaron la misma condición con otras palabras: **que existan presupuestos cerrados**. `docs/historias/sprint-2.md` la cumple con HU-12: *"Guardar una versión del presupuesto. Una versión cerrada no puede modificarse; los cambios posteriores generan una nueva versión."*

### Qué no cambia

El **borrador** —lo que hoy calcula el cómputo en vivo, `project_recipe` más la query de ADR-003 §2— sigue leyendo siempre el precio y la receta actuales. Ni ADR-003 §6 ("la obra referencia el catálogo, no lo copia") ni ADR-005 §5 ("el precio es vivo: el cómputo se recalcula") se tocan para el borrador. Esta ADR agrega un **segundo artefacto**, la versión, donde recién ahí se congela — no cambia cómo se calcula lo que todavía no se guardó.

### Qué restringe la decisión

`docs/historias/sprint-2.md`, HU-11 y HU-12 completas. Los puntos que definen el esquema:

- El presupuesto se agrupa en tres bloques — Materiales, Mano de obra, Equipos — y es lo que HU-11 ya calcula en vivo; HU-12 lo congela tal cual está en ese momento.
- "Guardar versión" lleva nombre/nota opcional, numeración correlativa **por obra**, y congela cantidad + precio unitario + subtotal de cada recurso, más las líneas de cómputo que la generaron.
- Una versión guardada **nunca se edita**: no existe endpoint de edición: cualquier cambio posterior es una versión nueva.
- Cambios de precio o de receta posteriores a guardar **no alteran** una versión ya guardada.
- "Cargar esta versión" reemplaza las líneas del borrador (soft-delete de las actuales) y **recalcula a precios actuales** — no revive los precios congelados.
- Si la receta de una línea de la versión fue dada de baja desde entonces, esa línea no se carga y la pantalla dice cuál quedó afuera.
- No se puede guardar una versión con el cómputo vacío.
- Guardar y cargar piden un permiso nuevo de obra para `lead`/`collaborator`; ver versiones pide lo mismo que ver el costo (`project.cost.view` o `project.view_all`) — el `client` no las ve.

---

## Decisión

### 1. Tres tablas nuevas

Ninguna existe hoy — a diferencia de ADR-006, esto no extiende una tabla, la agrega entera.

```
BUDGET_VERSION {
    bigint id PK
    bigint project_id FK
    bigint firm_id FK "redundante a proposito, igual que project_recipe"
    integer version_number "CHECK > 0, correlativo por obra"
    varchar note "opcional, nombre y nota son un solo campo"
    numeric total "CHECK >= 0, suma de subtotales ya redondeados"
    char currency
    timestamptz prices_as_of "minimo price_updated_at al congelar"
    bigint created_by FK account
    timestamptz created_at
}

BUDGET_VERSION_ITEM {
    bigint id PK
    bigint budget_version_id FK "ON DELETE CASCADE"
    bigint resource_id "sin FK: copiado, no referenciado"
    varchar resource_name "copiado"
    varchar resource_type "copiado: material | labor | equipment"
    varchar unit_abbreviation "copiado"
    numeric quantity "CHECK > 0"
    numeric unit_price "CHECK >= 0"
    char currency
    numeric subtotal "CHECK >= 0, quantity x unit_price"
}

BUDGET_VERSION_LINE {
    bigint id PK
    bigint budget_version_id FK "ON DELETE CASCADE"
    bigint recipe_id FK "viva: hace falta para poder cargar de nuevo"
    numeric quantity "CHECK > 0, copiada de project_recipe"
    varchar note "copiada de project_recipe"
}
```

`budget_version` no lleva `is_active` ni `updated_at`. No hay baja lógica de versiones — HU-12 la deja fuera de alcance explícitamente ("borrar versiones") — y una fila que por regla de negocio nunca se actualiza no necesita el trigger de `updated_at` (`docs/modelo-datos-sprint-1.md` §3.11): es la primera tabla del proyecto donde ese trigger no aplica, con el mismo espíritu con que `recipe_resource` ya omite timestamps por ser vínculo puro.

`budget_version_item` y `budget_version_line` tampoco llevan `is_active`/`updated_at`, por el mismo motivo: son detalle de un agregado inmutable, no entidades con ciclo propio. `ON DELETE CASCADE` desde `budget_version` es correcto ahí aunque la regla general (`modelo-datos §3.3`) diga que una FK a datos de negocio nunca hace cascada: esa regla es sobre entidades, y un ítem o una línea de versión no lo son — son composición pura del mismo agregado, la misma categoría que ya ocupa `recipe_resource` respecto de `recipe`.

Restricciones: `UNIQUE (project_id, version_number)` (`uq_budget_version_project_number`) y la FK compuesta de siempre para aislar el tenant:

```
(project_id, firm_id) → project (id, firm_id)
```

`budget_version_item` y `budget_version_line` no necesitan su propia FK compuesta contra `project`: solo son alcanzables a través de `budget_version_id`, y esa fila ya quedó atada al estudio correcto. Repetir `firm_id` un nivel más abajo no protegería nada que la FK de arriba no proteja ya.

### 2. Ítem congelado: copiado, no referenciado. Línea: referenciada, porque hay que poder recargarla

Son dos trabajos distintos, y el texto de la tarea los separa a propósito.

El **ítem** (`budget_version_item`) existe para *mostrar* los números tal como quedaron el día que se guardó la versión, para siempre. `resource_id` viaja sin FK, deliberadamente: el punto de un ítem congelado es que no necesite que nada siga existiendo para poder mostrarse — es un comprobante, no una vista sobre datos vivos. Se deja como columna informativa (útil para un eventual link "ver este material hoy"), pero la integridad de la fila no depende de que ese id siga siendo válido.

La **línea** (`budget_version_line`) existe para *reconstruir* el borrador cuando alguien aprieta "Cargar esta versión", y HU-12 pide con todas las letras que esa reconstrucción recalcule a precios vigentes y respete si la receta **sigue activa hoy**. Eso exige leer el estado actual de `recipe`, así que acá la referencia tiene que ser viva — `recipe_id` es una FK real.

### 3. Numeración correlativa por obra

Se calcula en la transacción de guardado: `SELECT COALESCE(MAX(version_number), 0) + 1 FROM budget_version WHERE project_id = :id`, bajo lock de la fila `project` (`SELECT ... FOR UPDATE`, que la ruta ya carga para resolver visibilidad — el lock es gratis) para que dos guardados simultáneos no calculen el mismo número, con `UNIQUE (project_id, version_number)` como respaldo final si algo se escapa.

Se descarta una columna contador en `project` (tocaría una tabla que ADR-002 declara cerrada, por algo que le pertenece únicamente a este módulo) y una secuencia nativa de Postgres (no hay forma directa de tener "una secuencia por obra" sin SQL dinámico por proyecto).

### 4. Permiso nuevo

El texto de T-05 dice "permisos nuevos" en plural; HU-12 lo precisa a uno solo: *"Guardar y cargar exigen un permiso nuevo de obra (lead, collaborator)"*.

| Ámbito | Código | Roles que lo reciben |
|---|---|---|
| `project` | `project.budget.manage` | `lead`, `collaborator` |

Uno solo para guardar **y** cargar, mismo argumento que ADR-005 §2 y que ADR-006 §3: no hay ningún rol al que le corresponda una acción sin la otra.

**Ver versiones no suma permiso nuevo.** Reusa `project.cost.view` **o** `project.view_all` (ADR-003 §8), con el mismo `requires_any` que ya protege el `GET` del cómputo en `app/api/routes/takeoff.py` — HU-12 lo pide literal: "lo mismo que ver el costo". Se deja explícito acá porque es fácil asumir por default que toda capacidad nueva trae su propio permiso; en este caso se decide activamente que no, y por eso el `client` (que no tiene `project.cost.view`) tampoco ve versiones.

Se agrega en la migración de seed, mismo mecanismo que `b97f764e437b_seed_recipe_catalog_permissions.py`.

### 5. Reglas que el esquema no puede garantizar

Cada una con su test, mismo formato que ADR-005 §7 y ADR-006 §4:

1. **No se puede guardar una versión con el cómputo vacío.** El servicio de guardado cuenta las líneas activas de `project_recipe` de la obra antes de crear `budget_version`; si son cero, levanta un error de dominio (mismo patrón que ya usa `takeoff.py` para "la receta necesita al menos una línea") → 409, y no se escribe ninguna fila. Test: `POST .../budget/versions` sobre una obra sin líneas activas → 409, cero filas nuevas en `budget_version`.
2. **Una versión guardada nunca se edita.** No existe ningún endpoint `PUT`/`PATCH` bajo `/budget/versions`, ni una función de servicio que actualice una fila ya creada — la garantía es la ausencia de ese código, igual que "ningún endpoint escribía en el catálogo" antes de ADR-005. Test sobre la tabla de rutas de FastAPI (mismo idioma que `modelo-datos §6`): el prefijo `/budget/versions` solo registra `POST` (crear) y `POST .../load` (cargar), nunca `PUT`/`PATCH`/`DELETE`.
3. **"Cargar" da de baja las líneas actuales del borrador y crea nuevas desde la versión, a precios vigentes.** Servicio `load_version`, en una sola transacción: (a) `is_active = False` en todas las líneas activas de `project_recipe` de la obra — mismo mecanismo que `remove_line` de `takeoff.py`, nunca `DELETE`; (b) por cada `budget_version_line` cuya receta sigue activa, crear una `ProjectRecipe` nueva copiando `recipe_id`, `quantity` y `note` — el precio sale solo, porque una `ProjectRecipe` nueva siempre calcula contra el precio vivo del recurso (ADR-005 §5 intacta); (c) las líneas cuya receta fue dada de baja se omiten y se devuelven en la respuesta como "quedaron afuera". Test: guardar una versión → dar de baja una de sus recetas desde el catálogo → cargar la versión → esa línea no aparece en el borrador resultante y la respuesta la lista como omitida; las demás se recrean con el precio de hoy, no el congelado.
4. **La numeración correlativa la garantiza el esquema a medias.** Que no haya dos versiones con el mismo número en la misma obra lo asegura `UNIQUE (project_id, version_number)`; qué número le corresponde a la próxima lo decide el servicio, con el lock descrito en §3. Vale la pena anotarlo así de explícito: es el caso donde el esquema pone el piso de seguridad y el servicio decide el valor.

### 6. Rutas nuevas

Calcadas de la forma de `app/api/routes/takeoff.py` (mismo prefijo `/firms/{firm_id}/projects/{project_id}/...`, mismo 404 de obra ajena):

- `POST .../budget/versions` — `project.budget.manage`.
- `GET .../budget/versions` — `requires_any(("project.cost.view", "project"), ("project.view_all", "firm"))`.
- `GET .../budget/versions/{version_id}` — mismo `requires_any`.
- `POST .../budget/versions/{version_id}/load` — `project.budget.manage`.

Deliberadamente **sin** `PUT`/`PATCH`/`DELETE`: es la regla de servicio 2 hecha topología de rutas, no solo un chequeo de autorización.

---

## Consecuencias

**Se desbloquea:**

- HU-12 queda definida y se puede estimar, ya con HU-11 (el borrador agrupado) como su fuente directa.
- El estudio puede presentarle al cliente un presupuesto que no cambia si el soporte actualiza un precio al día siguiente — lo que ADR-005 §5 asumía como costo aceptado hasta que existiera este artefacto.
- Un presupuesto cerrado queda protegido de que una receta se corrija o se dé de baja después — lo que ADR-003 §6 dejaba pendiente para cuando hubiera presupuestos cerrados.

**Compromisos que asumimos:**

- **El borrador y la versión pueden mostrar números distintos para "lo mismo" el mismo día** — es la consecuencia directa y buscada de congelar: si el estudio actualiza un precio después de guardar, el borrador lo refleja y la versión no. La pantalla de detalle de una versión tiene que mostrar su `prices_as_of`, igual que hoy lo hace el borrador (ADR-005 §5), para que la diferencia sea legible y no un error aparente.
- **Cargar una versión vieja no reproduce el presupuesto de aquel momento**, reproduce las cantidades de aquel momento a los precios de hoy — es intencional (HU-12 lo pide así: "recalcula a precios actuales"), pero hay que decirlo explícito para que nadie lo lea como un bug.
- **Tres tablas más para mantener**, sin baja lógica ni auditoría de cambios propia — coherente con que no cambian nunca, pero significa que un error al guardar una versión (ej. un precio mal congelado por un bug) no tiene camino de corrección salvo guardar una versión nueva.

**Queda pendiente de revisar, y bajo qué condición:**

| Tema | Se revisa cuando |
|---|---|
| Comparar dos versiones lado a lado | Se pida explícitamente — hoy HU-12 lo deja fuera de alcance |
| Exportar una versión a PDF o compartirla con el cliente | Se pida explícitamente |
| Aprobación o firma de una versión | El estudio necesite un flujo formal de aceptación con su cliente |
| Borrar versiones | Aparezca un caso real de versiones guardadas por error que haya que limpiar |
| Recetas propias del estudio en `budget_version_line` (ADR-006) | Se implementa junta con ADR-006: una línea de versión puede apuntar a una receta de estudio igual que a una general, sin cambio de esquema — la FK es a `recipe.id` sin importar su `firm_id` |

---

## Alternativas descartadas

**Snapshot JSON de todo el presupuesto en una sola columna, en vez de tablas relacionales.** Menos tablas, menos migraciones. Descartada porque no se puede agrupar ni sumar en SQL para la pantalla de detalle (HU-11/HU-12 la piden agrupada en Materiales/Mano de obra/Equipos) sin parsear el blob en la aplicación, porque pierde los `CHECK`/`NOT NULL` que defienden cada invariante — `docs/modelo-datos-sprint-1.md` §6 pide un test por invariante de esquema, y un JSON no tiene ninguno que testear — y porque la regla "si la receta se dio de baja, se omite y se reporta" necesita acceso estructurado línea por línea al momento de cargar, no un blob opaco.

**Versionar `project_recipe` agregándole una columna `version_id`, en vez de tablas separadas.** Menos tablas nuevas. Descartada porque mezcla dos ciclos de vida en una sola tabla: el borrador es mutable y de precio vivo, una versión es inmutable y de precio congelado. Toda lectura del borrador tendría que acordarse de filtrar `version_id IS NULL` en todos lados — la misma trampa que `modelo-datos §3.3` ya advierte para `is_active` —, y habría que agregarle a `project_recipe` columnas de precio y subtotal que solo tienen sentido para las filas congeladas. Separar tablas deja a `project_recipe` intacta, tal como la definió ADR-003 §2: mismo principio aditivo que ADR-003 §6 ya usó para diferir la copia de receta.

**Un solo `budget_version_item`, sin `budget_version_line` separada.** Menos tablas. Descartada por granularidad: el ítem agrupa **por recurso** (lo que pide la pantalla de HU-11/HU-12), y la línea es **por entrada de cómputo** — hace falta para recargar fielmente dos líneas de la misma receta con notas distintas ("planta baja"/"planta alta", ADR-003 §5) como dos filas, no fundidas en una. Es el mismo desdoblamiento que ya existe en vivo entre `project_recipe` (líneas) y la agregación por recurso de la query de ADR-003 §2; congelar simplemente fija las dos vistas que ya se calculan hoy.

**Numeración global de versiones**, una sola secuencia para toda la plataforma en vez de correlativa por obra. Más simple de implementar. Descartada porque contradice literalmente lo pedido ("correlativo por obra", "v1, v2… por obra") y porque filtraría información entre estudios: uno podría inferir cuántas versiones guarda otro por los huecos en la numeración de sus propias obras — el mismo tipo de fuga que el modelo multi-tenant existe para evitar.

---

## Referencias

- [ADR-002](0002-authorization-model.md) §8 y §9.2 — aislamiento entre estudios y `requires_any`.
- [ADR-003](0003-recipe-catalog.md) §2 y §6 — el esquema del cómputo vivo y la decisión, ahora resuelta acá, de no copiar la receta a la obra.
- [ADR-005](0005-catalog-administration.md) §5 y §7 — el precio vivo del borrador, que esta ADR no toca, y el formato de "reglas que el esquema no puede garantizar".
- [ADR-006](0006-firm-recipes.md) — las recetas que `budget_version_line.recipe_id` puede referenciar, generales o de estudio, sin distinción de esquema.
