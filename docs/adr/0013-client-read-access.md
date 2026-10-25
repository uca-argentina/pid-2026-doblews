# ADR-013: Acceso de lectura del cliente a sus obras

**Estado:** Propuesta
**Fecha:** 2026-10-25
**Contexto:** Qué ve el cliente de una obra y cómo entra a sus obras. Deja firmes HU-25 y HU-26 del [Sprint 4](../historias/sprint-4.md). **Reemplaza en parte** la regla "el cliente no ve costos" de [ADR-003](0003-recipe-catalog.md) §8 y el permiso de lectura de versiones de [ADR-007](0007-budget-versions.md) §4. El resto de esas dos secciones sigue vigente.

---

## Contexto

### Qué pide la cátedra

> Agregar el rol Cliente, con acceso de solo lectura a sus obras: avance, cronograma y versiones de presupuesto.

### De dónde partimos

**El rol ya existe.** [ADR-002](0002-authorization-model.md) §7 sembró `client` en los dos ámbitos, y los sprints siguientes le fueron dando lectura:

| Ámbito | Permisos del `client` hoy | Qué le abren |
|---|---|---|
| `firm` | `firm.view`, `catalog.view` | el listado de sus obras y el catálogo |
| `project` | `project.view` | el detalle de la obra |
| `project` | `project.recipe.view` | el cómputo, **sin importes** (ADR-003 §8) |
| `project` | `project.task.view` | la planificación con su Gantt y el avance, **sin importes** ([ADR-009](0009-project-planning.md) §9) |

Así que de las tres cosas que pide el enunciado, **avance y cronograma ya los ve**. La que falta son las **versiones del presupuesto**, que hoy no ve por una decisión explícita: ADR-007 §4 resolvió que ver versiones pide "lo mismo que ver el costo", `project.cost.view`, y el `client` no lo tiene.

### Por qué se abre una excepción

ADR-003 §8 fijó que el cliente "ve su obra y no ve los costos internos del estudio". La regla sigue teniendo sentido para lo **interno y vivo**: el presupuesto que cambia mientras el arquitecto edita el cómputo, el costo de cada tarea, los precios de los proveedores, las órdenes. Una **versión guardada** es otra cosa: es un presupuesto congelado, con fecha y nota, que el estudio arma justamente para presentarle a alguien. Mostrarle al cliente lo que el estudio le presentó no expone el costo interno, y lo pide el enunciado.

Por eso no se le da `project.cost.view`, que le abriría todo lo de arriba. Se crea un permiso más angosto, solo para las versiones.

### Qué restringe la decisión

- [ADR-002](0002-authorization-model.md): permisos y nunca roles. "El cliente no ve menos, ve otra cosa" (§7).
- Una obra que no es suya responde **404**, como siempre.
- Decisiones del equipo al armar el sprint: el cliente ve las **versiones completas, con importes**, y tiene una vista propia, **"Mis obras"**.

---

## Decisión

### 1. Un permiso nuevo, solo para leer versiones

| Ámbito | Código | Roles |
|---|---|---|
| `project` | `project.budget_version.view` | `lead`, `collaborator`, `client` |

El guard de lectura de `app/api/routes/budget_versions.py` pasa de

```
requires_any(("project.cost.view", "project"), ("project.view_all", "firm"))
```

a

```
requires_any(("project.budget_version.view", "project"), ("project.view_all", "firm"))
```

para el listado y el detalle de versiones. **Guardar y cargar una versión siguen pidiendo `project.budget.manage`** (ADR-007 §4), que el cliente no tiene. `lead` y `collaborator` reciben el permiso nuevo para que nadie pierda lo que hoy ve, y el `owner` sigue entrando por `project.view_all`.

Entra en una migración de seed, con el mismo mecanismo que `b97f764e437b_seed_recipe_catalog_permissions.py`.

**`project.cost.view` sigue sin ser del cliente.** El test de RBAC que lo fija (`test_the_project_client_does_not_see_costs`) se mantiene tal cual, y se suma uno que fija la excepción: el `client` tiene `project.budget_version.view` y nada más que eso de costos.

### 2. Qué ve el cliente de su obra, y qué no

| Puerta | Permiso que la abre | ¿El `client` la ve? |
|---|---|---|
| Datos de la obra | `project.view` | Sí |
| Cómputo, cantidades | `project.recipe.view` | Sí, sin importes (como hoy) |
| Planificación y Gantt (el cronograma) | `project.task.view` | Sí, sin importes (como hoy) |
| Avance | `project.task.view` | Sí (como hoy) |
| **Versiones del presupuesto** | `project.budget_version.view` | **Sí, completas, con importes (nuevo)** |
| Presupuesto vivo (en Cómputo) | `project.cost.view` | No |
| Costo de las tareas | `project.cost.view` | No |
| Dashboard | `project.cost.view` | No |
| Compras y órdenes | `project.cost.view` / `purchase_order.view` | No |
| Proveedores y nivel | `supplier.view` / `purchase_order.view` | No |

**Todo es lectura.** Ninguna de las puertas que ve le da un permiso de escritura. En el front, cada botón de acción ya depende de su propio permiso (`project.task.manage`, `project.budget.manage`, etc.), así que no aparece para él. HU-25 lo verifica pantalla por pantalla, y cada puerta cerrada tiene su test (403 en la API, pestaña oculta en el front).

### 3. "Mis obras"

**Un endpoint de resumen**, `GET /firms/{firm_id}/projects/overview`, con el mismo guard que el listado de obras: `firm.view`, filtrado por las obras visibles (ADR-002 §7, "el listado se guarda con `firm.view`"). Por cada obra devuelve:

- el avance real y el planificado de la obra entera y el fin previsto, de la misma lectura que usan Avance y el dashboard (`app/api/planning_read.py`, ADR-009 §13 y §14);
- la **última versión** (número, fecha y total), solo si quien pide tiene `project.budget_version.view` en esa obra o `project.view_all`. Si no, viaja vacía.

No hay `project_id` en la URL, así que los permisos de obra se resuelven por obra dentro del endpoint, contra las mismas filas de `project_member` que usa `get_visible`.

**Quién la ve como pantalla de inicio:** quien **no tiene `project.create` ni `project.view_all`** en el estudio. Es una regla de permisos y no de rol: hoy la cumple solo el `client`, y si algún día existe otro rol de solo lectura, cae en la misma vista sin tocar código. Para los demás, el listado de obras sigue como está.

Dentro de una obra, el cliente navega las pestañas de la tabla de §2 que le corresponden. El menú del estudio ya filtra por permiso (`FirmNavbar`): no ve Proveedores ni Padrón, y no va a ver Órdenes ni Nivel.

### 4. Reglas, cada una con su test

1. El `client` lista y abre las versiones de su obra (200), y no puede guardar ni cargar una (403).
2. El `client` sigue recibiendo 403 en el presupuesto vivo, el dashboard, compras, órdenes y proveedores.
3. Un `client` no ve versiones de una obra que no es suya (404).
4. `lead`, `collaborator` y `owner` siguen viendo versiones como antes.
5. `overview` devuelve solo las obras visibles, y la última versión vacía para quien no puede verla.

---

## Consecuencias

**Se desbloquea:**

- HU-25 y HU-26.

**Compromisos que asumimos:**

- **La regla "el cliente no ve costos" tiene una excepción**, y queda escrita acá. Toda pantalla que muestre importes a un cliente tiene que poder justificarse con este permiso y no con `project.cost.view`.
- Una versión guardada pasa a ser algo que el cliente lee: lo que se pone en la nota de una versión lo va a ver él.
- Las versiones que se guardaron antes de este cambio también las ve: no hay versiones "internas" y versiones "para el cliente".

**Queda pendiente de revisar, y bajo qué condición:**

| Tema | Se revisa cuando |
|---|---|
| Versiones internas que el cliente no vea | El estudio quiera guardar borradores de presupuesto sin mostrarlos |
| Que el cliente apruebe o comente una versión | Se quiera registrar la aceptación del presupuesto |
| Descargar una versión en PDF | El cliente la necesite fuera del sistema |

---

## Alternativas descartadas

**Darle `project.cost.view` al cliente.** Una sola fila. Descartada porque le abre el presupuesto vivo, el costo de las tareas y el dashboard, que siguen siendo internos.

**Mostrarle solo los totales de cada versión.** Menos exposición. Descartada por decisión del equipo: el pedido dice "versiones de presupuesto", y una versión sin su detalle no le sirve al cliente para entender qué se le presupuestó.

**Marcar cada versión como visible o no para el cliente.** Más control. Descartada por ahora: agrega una columna y una decisión en cada guardado que nadie pidió. Queda en la tabla de pendientes.

**Un rol nuevo de "cliente con acceso a presupuestos".** Descartada porque el catálogo de roles es cerrado (ADR-002 §7) y el cliente que pide la cátedra es el que ya existe.

**Decidir "Mis obras" por rol (`if role == client`).** Más directo. Descartada porque rompe la regla de permisos y no roles. La condición "sin `project.create` ni `project.view_all`" dice lo mismo en el idioma del sistema.

**Un portal aparte, en otro dominio.** Separación total. Descartada por el costo de un segundo frontend y un segundo deploy para tres pantallas de lectura.

---

## Referencias

- [ADR-002](0002-authorization-model.md) §7 y §8 — catálogo de roles, el listado se guarda con `firm.view`, aislamiento.
- [ADR-003](0003-recipe-catalog.md) §8 — "el cliente no ve costos", que esta ADR acota.
- [ADR-007](0007-budget-versions.md) §4 — el permiso de lectura de versiones, que esta ADR cambia.
- [ADR-009](0009-project-planning.md) §9, §13 y §14 — planificación, avance y la lectura compartida con el dashboard.
- [sprint-4.md](../historias/sprint-4.md) — HU-25 y HU-26.
