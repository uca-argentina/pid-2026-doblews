# ADR-006: Recetas del estudio

**Estado:** Propuesta
**Fecha:** 2026-09-25
**Contexto:** Modelo de datos de las recetas propias de cada estudio. Desbloquea HU-9 del Sprint 2 y precisa el pendiente que dejó anotado [ADR-003](0003-recipe-catalog.md).

---

## Contexto

### Qué quedó pendiente

[ADR-003](0003-recipe-catalog.md) decidió que el catálogo de recetas es único, global y sembrado, y dejó anotado en su tabla de pendientes:

> Receta propia del estudio, editable | Un estudio pida ajustar proporciones según su experiencia

Esa condición ya se cumplió: `docs/historias/sprint-2.md` registra, en sus "Decisiones de alcance confirmadas" del 2026-09-22, que "receta creada por un arquitecto" significa **receta del estudio** — la crea `owner` o `architect`, es visible y usable por todas las obras de ese estudio, y nunca por otro. Esta ADR es esa decisión llevada a esquema.

### Qué no cambia

El catálogo del sistema sigue siendo lo que decidió ADR-003 y precisó [ADR-005](0005-catalog-administration.md): único, global, administrado por el `support`. Un arquitecto no puede editar ni dar de baja una receta general — eso sigue siendo privilegio del soporte. Lo que se agrega es una **segunda fuente** de recetas, propia de cada estudio, que convive con la primera sin tocarla.

### Qué restringe la decisión

- `docs/historias/sprint-2.md`, HU-9: nombre único **de la firma** (puede coincidir con el de una general — el origen las distingue); baja lógica que no rompe las líneas de cómputo ya cargadas; las recetas generales no muestran acciones de editar/dar de baja en esta pantalla, y llamar al endpoint directo sobre una general tiene que fallar; aislamiento entre estudios da 404; escribir exige un permiso nuevo.
- ADR-002 §8: el aislamiento entre estudios no lo resuelve el sistema de permisos, lo resuelve que toda lectura pase por el repositorio base y que exista un test de aislamiento por endpoint.
- `project_recipe.recipe_id` (ADR-003 §2) es una FK **plana** a una sola tabla `recipe`, no compuesta: el catálogo es global, así que hoy no hay contra qué comparar el estudio de una receta. Si `recipe` pasa a tener dueño, esa FK deja de alcanzar sola.
- `docs/modelo-datos-sprint-1.md` §3.4: la unicidad de un *label* (no de una identidad) bajo baja lógica es parcial, `WHERE is_active`, case-insensitive.

---

## Decisión

### 1. `recipe.firm_id`: nullable, general si es `NULL`

Se agrega una columna a la tabla existente:

```
RECIPE {
    bigint id PK
    varchar name
    text description
    bigint unit_of_measure_id FK
    bigint firm_id FK "nullable: NULL es general, con valor es del estudio"
    boolean is_active
    timestamptz created_at
    timestamptz updated_at
}
```

`NULL` = receta general del catálogo del sistema (lo que hoy ya existe, sin cambios de significado). Un valor = receta del estudio dueño de ese `firm_id`. No hay una tercera categoría y no hace falta: es la misma tabla, con un dueño opcional, igual que `project_recipe` ya reutiliza `recipe_resource` sin que esa tabla sepa de estudios.

La FK es **simple** contra `firm.id`, no compuesta: `recipe` no cuelga de ningún `project`, cuelga directo del estudio, así que no hay una segunda columna contra la cual atarla.

### 2. Nombre único dentro del estudio, entre activas — dos índices, no uno

Hoy existe un único índice parcial global, `uq_recipe_name_active` sobre `lower(name)` `WHERE is_active`, heredado de cuando toda receta era general. HU-9 pide dos cosas a la vez: que el nombre sea único **dentro del estudio**, y que **pueda coincidir** con el de una receta general. Un solo índice compuesto `(firm_id, lower(name)) WHERE is_active` no alcanza para eso: en Postgres, `NULL` nunca es igual a `NULL` dentro de un índice único, así que ese índice protegería la unicidad dentro de cada estudio con `firm_id` no nulo, pero dejaría pasar dos recetas generales con el mismo nombre sin ninguna protección — exactamente la garantía que existe hoy y que no se puede perder.

Se reemplaza por dos índices parciales:

```sql
CREATE UNIQUE INDEX uq_recipe_name_active_general
    ON recipe (lower(name))
    WHERE is_active AND firm_id IS NULL;

CREATE UNIQUE INDEX uq_recipe_name_active_firm
    ON recipe (firm_id, lower(name))
    WHERE is_active AND firm_id IS NOT NULL;
```

El primero es literalmente el índice de hoy, acotado a las generales. El segundo es nuevo: "dentro de este estudio, nombre único entre activas". Los dos nunca se comparan entre sí, así que una receta general y una de estudio pueden compartir nombre — que es exactamente lo que pide HU-9.

Se descarta colapsar `firm_id` con `coalesce(firm_id, 0)` en un solo índice compuesto: funciona, pero depende de que `0` nunca sea el id real de un estudio, un supuesto implícito que ninguna constraint garantiza. Dos índices con nombre explícito dicen en el catálogo de la base exactamente lo que hacen, sin ese supuesto escondido.

Se agrega también `ix_recipe_firm_id`, parcial `WHERE firm_id IS NOT NULL`, para la query frecuente de "las recetas de este estudio" (pantalla HU-9 y selector de HU-5).

### 3. Permiso nuevo: `recipe.manage`

| Ámbito | Código | Roles que lo reciben |
|---|---|---|
| `firm` | `recipe.manage` | `owner`, `architect` |

Un solo permiso para alta, edición y baja — no cuatro — con el mismo argumento que [ADR-005 §2](0005-catalog-administration.md) usó para `catalog.manage`: no existe ningún rol al que le corresponda una parte de esas acciones y no el resto.

No hace falta un permiso de lectura nuevo. `catalog.view` (ADR-003 §8, ya lo tienen `owner`, `architect` y `client`) sigue sirviendo para el `GET`: la pantalla de HU-9 lee generales y del estudio combinadas, que es exactamente lo que ya autoriza ese permiso — se agrega una columna de origen a la respuesta, no un permiso nuevo para verla.

Se agrega en la migración de seed de permisos, con el mismo mecanismo que `b97f764e437b_seed_recipe_catalog_permissions.py` y `5c12ccef2ab5_seed_catalog_manage_permission.py`: tablas de permiso/rol declaradas a mano en la migración, `bulk_insert`, ids resueltos por `(code, scope)`.

### 4. Reglas que el esquema no puede garantizar

Como en [ADR-005 §7](0005-catalog-administration.md), hace falta decirlo explícito porque estas reglas **se leen como si el esquema las sostuviera solo**, y no es así. Van en la capa de servicio, cada una con su test:

1. **Una línea de cómputo no puede usar una receta de otro estudio.** Si `recipe.firm_id` no es nulo, tiene que ser el de la obra. No se puede expresar como constraint: `project_recipe.recipe_id` es una FK plana (ADR-003 §6, el catálogo es global) y ningún `CHECK` compara contra otra tabla. Se extiende `_check_recipe` en `app/services/takeoff.py`, que hoy ya rechaza una receta inactiva, para que además rechace `firm_id IS NOT NULL AND firm_id != project.firm_id` — con el **mismo** mensaje de error (409, `RECIPE_NOT_AVAILABLE`) que usa para una receta dada de baja. Es deliberado: una receta de otro estudio y una receta retirada le tienen que resultar indistinguibles a quien consulta, con el mismo argumento anti-oráculo de [ADR-002 §9.2](0002-authorization-model.md) — lo contrario sería confirmarle a un estudio que otro tiene una receta con determinado nombre. Test: crear una línea de cómputo en una obra del estudio A apuntando al id de una receta cuyo `firm_id` es B → 409, mismo cuerpo de respuesta que una receta inactiva.
2. **Una receta general no se escribe desde ninguna ruta de `/firms/{firm_id}`.** No es una regla de integridad de datos, es de enrutamiento: nada en el esquema impide que un `UPDATE` alcance una fila con `firm_id IS NULL`. Toda escritura bajo `/firms/{firm_id}/recipes/...` resuelve el `recipe_id` exigiendo `Recipe.firm_id == firm_id` **literal** — nunca `IS NULL`, nunca "cualquier estudio". Si la fila es general o de otro estudio, la query no la trae → **404**, no 403, mismo criterio de aislamiento que ADR-002 §9.2 aplicado acá: la ruta de un estudio no revela que existe una receta que no es suya, general o ajena, por igual. Esto encaja directo con `FirmScopedRepository` (`app/repositories/base.py`), que ya exige `firm_id` + `is_active` en cualquier modelo que lo use: con `recipe.firm_id` agregado, un repositorio de recetas de estudio construido sobre esa base excluye las generales sin escribir un chequeo aparte — `WHERE firm_id = :firm_id` nunca iguala un `NULL`. Test de aislamiento: `PUT /firms/{A}/recipes/{id de una general}` → 404; mismo caso con el id de una receta del estudio B.
3. **Una receta del estudio solo lleva recursos activos del catálogo del sistema.** No hay catálogo de materiales por estudio — HU-9 lo deja fuera de alcance explícitamente — así que la validación es la misma que ya existe para el alta del soporte: `_validate_recipe_resources` en `app/services/catalog_admin.py`, reusada desde el nuevo servicio de recetas de estudio en vez de reescrita. Test: crear una receta de estudio con una línea a un recurso `is_active = False` → 422, mismo contrato que hoy (`InvalidReferenceError`).

### 5. Rutas nuevas

`/firms/{firm_id}/recipes` y `/firms/{firm_id}/recipes/{recipe_id}`, calcadas de la forma de `app/api/routes/catalog_admin.py` pero de ámbito `firm` en vez de `platform`:

- `GET /firms/{firm_id}/recipes` — `catalog.view`. Trae generales + las del estudio, cada una con su origen. Es una query nueva en `app/services/catalog.py` (`firm_id IS NULL OR firm_id = :firm_id`), **no** un caso de `FirmScopedRepository`: ese repositorio excluye estructuralmente las generales, que es su virtud para la escritura (regla 2) y su límite para esta lectura combinada — son necesidades distintas, no una carencia del repositorio.
- `POST /firms/{firm_id}/recipes` — `recipe.manage`. `firm_id` siempre sale de la URL, nunca del body.
- `PUT /firms/{firm_id}/recipes/{recipe_id}` — `recipe.manage`, resuelto vía el repositorio de estudio (regla 2).
- `DELETE /firms/{firm_id}/recipes/{recipe_id}` — `recipe.manage`. Baja lógica sin guardia de uso, igual que `deactivate_recipe` en ADR-005 §6: las líneas de cómputo ya cargadas con esa receta siguen calculando.

Consecuencia sobre lo existente: `add_line` (HU-5, `app/services/takeoff.py`) pasa a ofrecer generales + las del estudio del proyecto, y su `_check_recipe` incorpora la regla 1 de esta sección.

---

## Consecuencias

**Se desbloquea:**

- HU-9 queda definida y se puede estimar.
- Un estudio deja de estar atado al catálogo global cuando su forma de trabajar no coincide con la receta sembrada — la condición que ADR-003 dejaba pendiente.
- El editor de recetas de HU-9 puede reusar el mismo maestro-detalle de HU-8 (ADR-005 §3), porque `recipe`/`recipe_resource` no cambian de forma, solo ganan un dueño opcional.

**Compromisos que asumimos:**

- **Dos índices de unicidad en vez de uno** sobre la misma tabla, que hay que mantener consistentes si el criterio de unicidad vuelve a cambiar.
- **Toda ruta nueva bajo `/firms/{firm_id}/recipes` tiene que resolver el `recipe_id` por el repositorio de estudio**, nunca por un `SELECT` directo — es la única barrera contra la regla 2, y no hay constraint que la reemplace si alguien la escribe mal.
- El aislamiento entre estudios para recetas propias queda sostenido por los mismos dos mecanismos de ADR-002 §8 (repositorio base + test por endpoint), no por algo nuevo — hay que agregar los casos de recetas a esa suite, no crear una aparte.

**Queda pendiente de revisar, y bajo qué condición:**

| Tema | Se revisa cuando |
|---|---|
| Recetas de estudio compartidas entre estudios (obras conjuntas) | Un estudio pida colaborar con otro en una misma obra |
| Duplicar una receta general para personalizarla desde sus líneas | Se pida explícitamente — hoy HU-9 lo deja fuera de alcance |
| Materiales propios del estudio, no solo recetas | Un estudio necesite un insumo que el catálogo global no tiene |
| Historial de cambios de una receta de estudio | Más de una persona edite las recetas del mismo estudio |

---

## Alternativas descartadas

**Tabla `firm_recipe` separada, con su propia `firm_recipe_resource`.** Simetría más clara entre "lo global" y "lo del estudio". Descartada porque `project_recipe.recipe_id` es hoy una FK plana a una sola tabla (ADR-003 §6); partirla en dos obliga a que esa FK deje de ser simple o se vuelva polimórfica sin integridad referencial real — el mismo problema que ADR-002 §5 ya evitó al descartar `role_assignment` polimórfica. Cada consumidor futuro (HU-11 agrupa por recurso, HU-12 congela ítems) tendría que unir contra dos tablas en vez de una. Es el caso que `docs/modelo-datos-sprint-1.md` §1.2 describe: agregar una columna nullable es barato; partir una tabla en dos con FKs de otras tablas ya cargadas encima es caro.

**Copiar la receta general al estudio como semilla al crearlo, para que el arquitecto la "edite como propia".** Resuelve el arranque con datos ya cargados. Descartada por el mismo motivo que ADR-003 ya usó para descartar "semilla global copiada a cada estudio": las correcciones que el soporte haga a una receta general nunca llegarían a las copias ya hechas, y quedarían N versiones divergentes de la misma receta.

**Un permiso de lectura nuevo, `recipe.view` de ámbito estudio, separado de `catalog.manage`/`catalog.view`.** Más explícito sobre qué habilita cada cosa. Descartada porque la pantalla de HU-9 no distingue entre ver el catálogo general y ver el propio: es una sola vista combinada, y `catalog.view` ya la cubre sin que nadie tenga que acordarse de sembrar un permiso más.

---

## Referencias

- [ADR-002](0002-authorization-model.md) §8 y §9.2 — aislamiento entre estudios y el criterio 404-no-403.
- [ADR-003](0003-recipe-catalog.md) §2, §6 y §8 — el esquema de cinco tablas, la FK plana de `project_recipe.recipe_id`, y el permiso `catalog.view`.
- [ADR-005](0005-catalog-administration.md) §2, §3 y §7 — el patrón de un solo permiso `*.manage`, el maestro-detalle de recetas, y el formato de "reglas que el esquema no puede garantizar".
- `docs/modelo-datos-sprint-1.md` §3.4 — unicidad parcial de un *label* bajo baja lógica.
