# Historias de Usuario — Sprint 2

**Materia:** Proyecto Integral de Desarrollo — UCAio
**Duración del sprint:** 2 semanas
**Equipo:** 2-3 personas (fullstack)

## Requerimientos de la cátedra

Texto recibido para este sprint, sin editar:

> Incorporar recetas constructivas. Una receta define los materiales y cantidades requeridas por unidad; por ejemplo, materiales necesarios para 1 m² de pared.
> Al aplicar una receta a un componente, calcular automáticamente las cantidades totales de cada material.
> Las recetas pueden ser generales o creadas por un arquitecto. Las generales no pueden modificarse ni eliminarse.
> Permitir asignar mano de obra y equipamiento con cantidad de horas y costo por hora.
> Generar el presupuesto estimado de la obra agrupado por materiales.
> Guardar una versión del presupuesto. Una versión cerrada no puede modificarse; los cambios posteriores generan una nueva versión.

## Qué ya está cubierto y qué es nuevo

Parte del pedido ya lo resolvió el Sprint 1. Esta tabla es la que conviene mostrar en la defensa para que se vea que cada oración del requerimiento tiene dueño.

| Requerimiento | Dónde se resuelve | Estado |
|---|---|---|
| Una receta define materiales y cantidades por unidad | [ADR-003](../adr/0003-recipe-catalog.md), HU-4 (consulta) y HU-8 (ABM del soporte) | **Hecho** en el Sprint 1 |
| Aplicar una receta a un componente calcula las cantidades totales | HU-5 (cómputo de la obra) | **Hecho** para materiales; se extiende a mano de obra y equipo en HU-10 |
| Recetas generales o creadas por un arquitecto | **HU-9** | Nuevo |
| Las generales no pueden modificarse ni eliminarse | **HU-9** | Nuevo (para el arquitecto; el soporte las sigue administrando) |
| Mano de obra y equipamiento con horas y costo por hora | **T-06** + **HU-10** | Nuevo |
| Presupuesto estimado agrupado por materiales | **HU-11** | Nuevo (evoluciona el cómputo de HU-5) |
| Guardar versiones del presupuesto; una cerrada no se modifica | **HU-12** | Nuevo |

## Decisiones de alcance confirmadas

Todo lo que el Sprint 1 dejó fijado sigue valiendo: plataforma **multi-estudio**, los endpoints chequean **permisos y nunca roles** ([ADR-002](../adr/0002-authorization-model.md)), recurso ajeno → **404**, **baja lógica** en todo, precios en **ARS** con `currency` modelado, y el catálogo del sistema es único y global ([ADR-003](../adr/0003-recipe-catalog.md), [ADR-005](../adr/0005-catalog-administration.md)).

Decidido el 2026-09-22 al leer los requerimientos nuevos:

- **"Receta creada por un arquitecto" = receta del estudio.** La crea un `owner` o un `architect`, y la ven y usan todas las obras de ese estudio. Nunca la ve otro estudio. Es el pendiente "receta propia del estudio, editable" que ADR-003 dejó anotado.
- **"Receta general" = el catálogo del sistema que ya existe.** El arquitecto no puede modificarla ni darla de baja. Quien la mantiene sigue siendo el soporte, por las pantallas de HU-8: si no, los precios envejecerían sin que nadie pudiera corregirlos, que es el problema que ADR-005 resolvió.
- **"Componente" = la línea de cómputo de HU-5** (receta + cantidad + nota: "Pared 15cm — planta baja, 120 m²"). No hay tabla nueva de componentes: la línea ya es "esta receta aplicada a esta parte de la obra", y la composición de componentes dentro de componentes sigue descartada (ADR-003).
- **La mano de obra y el equipo van dentro de la receta**, como recursos de tipo `labor` y `equipment`. Es exactamente el APU que ADR-003 §3 anticipó: el precio del recurso es el **costo por hora** y el rendimiento de la línea son las **horas por unidad** de receta ("1 m² de pared lleva 0,5 h de oficial"). No hay tablas nuevas: el `CHECK` de `resource.type` ya admite los dos valores.
- **Versiones del presupuesto: el cómputo vivo es el borrador.** Se sigue editando como hasta ahora; "Guardar versión" congela en ese momento cantidades y precios en una versión inmutable. Hay una pantalla de versiones para consultarlas y para **cargar una vieja** en el borrador y seguir desde ahí. Cualquier cambio posterior se guarda como una versión nueva: nunca se edita una guardada.

---

## T-05 — ADRs del sprint

*Tarea de equipo, no historia de usuario. Va primero: HU-9 y HU-12 cambian el modelo de datos, y el `CLAUDE.md` del repo pide la ADR antes que el código.*

- **ADR-006 — Recetas del estudio.** `recipe.firm_id` nullable: `NULL` es general, con valor es del estudio. Nombre único **dentro del estudio** entre activas. Permiso nuevo de ámbito estudio, `recipe.manage`, para `owner` y `architect`. Reglas que el esquema no garantiza y van en servicio, cada una con su test: una línea de cómputo no puede usar una receta de otro estudio (el `firm_id` de la receta, si lo tiene, tiene que ser el de la obra); una receta general no se escribe desde ninguna ruta de `/firms/{firm_id}`; una receta del estudio solo lleva recursos activos del catálogo del sistema.
- **ADR-007 — Versiones del presupuesto.** Tablas `budget_version` (obra, número correlativo por obra, nombre/nota, autor, fecha, total) + sus ítems congelados (recurso, tipo, unidad, cantidad, precio unitario y subtotal **copiados**, no referenciados) + sus líneas (receta, cantidad, nota) para poder cargarla de nuevo. Resuelve dos pendientes: "congelar el precio" de ADR-005 y "copia de la receta hacia la obra" de ADR-003, que se revisaban justamente cuando existieran presupuestos cerrados. Permisos nuevos de obra.
- **Mano de obra y equipo** no necesitan ADR nueva: es la misma decisión de ADR-003 §3, que se precisa editándola (unidad `h`, precio = costo por hora, rendimiento = horas por unidad).

**Depende de:** nada.
**Estimación:** 1 día, de a dos.

---

## T-06 — Unidad "hora" y seed de mano de obra y equipo

*Habilitadora técnica: sin ella HU-10 y HU-11 no tienen nada que mostrar.*

- Migración que agrega `h` (hora) a `unit_of_measure`. El catálogo de unidades sigue cerrado por migración (HU-0).
- Recursos semilla de tipo `labor` (`Oficial`, `Ayudante`) y `equipment` (`Hormigonera`), con unidad `h` y costo por hora de referencia.
- Las tres recetas sembradas (pared, contrapiso, carpeta) suman sus horas por m², para que el presupuesto de la obra de demo "Casa Rodríguez" tenga las tres secciones con datos.
- Como en T-04, el seed **no pisa** lo editado por pantalla (ADR-005 §4).

Cierra lo que T-04 dejó pendiente: "si los materiales `labor` y `equipment` se siembran alguna vez".

**Depende de:** T-05.
**Estimación:** 1 día. Lo caro, igual que en T-04, es curar los rendimientos, no el DDL.

---

## HU-9 — Recetas propias del estudio

> Como **arquitecto**, quiero crear, editar y dar de baja recetas propias de mi estudio, para computar trabajos que el catálogo general no contempla o que resolvemos distinto, sin poder alterar las recetas generales que usan todos.

**Criterios de aceptación**

- En la sección "Catálogo" del estudio, la vista **Recetas** lista las generales y las del estudio, cada una con su origen visible ("General" / "Del estudio"), y se puede filtrar por origen.
- Alta y edición de una receta del estudio: nombre, unidad, descripción y líneas (recurso del catálogo del sistema + cantidad por **1 unidad** de receta, numérica > 0). La unidad se elige del catálogo cerrado de HU-0.
- Una receta tiene **al menos una línea** y no repite recurso.
- El nombre es único entre las recetas activas **del estudio**. Puede coincidir con el de una general: el origen las distingue.
- Baja lógica. Una receta dada de baja deja de ofrecerse para cargar, pero las líneas de cómputo que ya la usan siguen calculando (mismo criterio que ADR-005 §6).
- **Las recetas generales no muestran acciones de edición ni de baja**, y si alguien llama igual al endpoint con el id de una general, recibe error. Solo el soporte las modifica, por HU-8.
- El alta de una línea de cómputo (HU-5) ofrece las generales y las del estudio, con su origen visible.
- Aislamiento: una receta de otro estudio no aparece en ningún listado y, pedida por URL, da **404**. Usada en una línea de cómputo da **409**, la misma respuesta que una receta dada de baja o inexistente, para no confirmar que existe en otro estudio (precisado al implementar, ver [ADR-006 §4](../adr/0006-firm-recipes.md)).
- La sección exige `recipe.manage` para escribir (`owner`, `architect`). Un `client` ve las recetas del estudio (tiene `catalog.view`) pero sin acciones.
- El editor se usa bien a 375px (reusa el modal maestro-detalle de HU-8).

**Fuera de alcance:** duplicar una receta general para personalizarla; materiales propios del estudio (las líneas usan solo recursos del catálogo del sistema); precios por estudio; compartir recetas entre estudios; composición de recetas dentro de recetas.
**Depende de:** T-05 (ADR-006) y HU-4/HU-8 (se reusan el buscador y el editor).
**Estimación:** 2,5 días.
**Definida por:** ADR-006 (T-05).

---

## HU-10 — Mano de obra y equipo en las recetas

> Como **arquitecto**, quiero que las recetas incluyan las horas de mano de obra y de equipo que lleva cada unidad, con su costo por hora, para que el cómputo de mi obra refleje el costo real del trabajo y no solo el de los materiales.

**Criterios de aceptación**

- El soporte da de alta, edita y da de baja recursos de tipo **mano de obra** y **equipo** desde las pantallas de HU-8, con unidad `h` y precio de referencia expresado como **costo por hora**. El listado muestra y filtra el tipo.
- Una receta —general o del estudio— puede llevar líneas de mano de obra y de equipo con **horas por unidad** de receta (numérica > 0), en el mismo editor que los materiales.
- Al aplicar una receta a la obra (HU-5), el cómputo calcula para cada recurso las **horas totales** (cantidad de la línea × horas por unidad) y su costo (horas totales × costo por hora), sumando todas las líneas, igual que ya hace con los materiales.
- Un recurso de mano de obra usado por una receta activa no se puede dar de baja (misma regla que los materiales, ADR-005 §7).
- El `client` de la obra ve las horas y no los costos (`project.cost.view`), igual que con los materiales.
- Las pantallas afectadas se ven bien a 375px.

**Fuera de alcance:** mano de obra o equipo cargados a mano en la obra, fuera de una receta; categorías salariales o convenios (UOCRA); cargas sociales; jornales en vez de horas; alquiler de equipo por día.
**Depende de:** T-06 (unidad `h` y seed).
**Estimación:** 1,5 días.
**Definida por:** [ADR-003 §3](../adr/0003-recipe-catalog.md), precisada en T-05.

---

## HU-11 — Presupuesto estimado de la obra

> Como **arquitecto**, quiero ver el presupuesto estimado de mi obra agrupado por recurso, separado en materiales, mano de obra y equipo, para saber cuánto va a costar y en qué se va la plata.

**Criterios de aceptación**

- Dentro de la obra hay una sección "Presupuesto" con tres grupos: **Materiales**, **Mano de obra** y **Equipos**.
- Cada grupo lista sus recursos con: nombre, unidad, cantidad total, precio unitario de referencia y subtotal.
- Cada grupo muestra su subtotal, y el presupuesto su **total general**. Los totales suman exacto lo que se ve en pantalla (se suman los importes ya redondeados, como en HU-5).
- El presupuesto dice que sus importes son "precios de referencia al \<fecha\>" (ADR-005 §5).
- Se recalcula solo: cambia al editar las líneas del cómputo o al cambiar un precio del catálogo. Es el **borrador** que HU-12 guarda como versión.
- Si la obra no tiene líneas, estado vacío con un llamado a cargar el cómputo.
- Exige `project.cost.view` o `project.view_all` (el `owner` lo ve en obras que no integra, como en HU-5). **El `client` no ve la sección.**
- Se ve bien a 375px: tarjetas por recurso en mobile, no tabla horizontal.

**Fuera de alcance:** costos indirectos, gastos generales, beneficio e IVA; agrupar por rubro o capítulo; exportar a PDF o Excel; precios por proveedor.
**Depende de:** HU-5 y HU-10.
**Estimación:** 1,5 días.

---

## HU-12 — Versiones del presupuesto

> Como **arquitecto**, quiero guardar versiones del presupuesto de mi obra y poder volver a una anterior, para tener un registro fijo de lo que le presenté al cliente mientras sigo ajustando el cómputo.

**Criterios de aceptación**

- En la sección "Presupuesto" hay un botón **"Guardar versión"**, con nombre o nota opcional ("Presentado al cliente 20/10").
- Guardar una versión **congela** el presupuesto de ese momento: cada ítem con su cantidad, precio unitario y subtotal, y las líneas del cómputo que lo generaron. Las versiones se numeran correlativas por obra (v1, v2, …).
- **Una versión guardada no se modifica nunca.** No existe endpoint para editarla; cualquier cambio posterior se hace en el borrador y se guarda como una versión nueva.
- Cambiar un precio del catálogo o una receta **no altera** las versiones ya guardadas: una versión muestra los números con los que se guardó.
- Pantalla **"Versiones"** con el listado: número, nombre/nota, fecha, autor y total.
- Detalle de una versión, de solo lectura, con el mismo formato agrupado de HU-11 y la fecha de los precios con los que se guardó.
- **"Cargar esta versión"** reemplaza las líneas del borrador por las de la versión, previa confirmación. Las líneas actuales se dan de baja (lógica), no se borran. El borrador cargado vuelve a calcular con los **precios vigentes**: la versión vieja sigue intacta.
- Si una receta de la versión se dio de baja desde entonces, esa línea no se carga y la pantalla dice cuál quedó afuera.
- No se puede guardar una versión con el cómputo vacío.
- Guardar y cargar exigen un permiso nuevo de obra (`lead`, `collaborator`). Ver las versiones exige lo mismo que ver el costo (`project.cost.view` o `project.view_all`): **el `client` no las ve**.
- Se usa bien a 375px.

**Fuera de alcance:** comparar dos versiones lado a lado; enviar una versión al cliente o darle acceso a ella; exportar a PDF; borrar versiones; aprobación o firma de una versión.
**Depende de:** T-05 (ADR-007) y HU-11.
**Estimación:** 2,5 días.
**Definida por:** ADR-007 (T-05).

---

## T-07 — Deploy y promoción `dev → main`

*Arrastrada del Sprint 1.*

El CI corre lint, migraciones, tests y build, pero no deploya. Sin ambiente de deploy **ninguna historia cumple la Definition of Done** ([reglas-de-trabajo §3](../reglas-de-trabajo.md), punto 4) y la demo se muestra desde localhost. Incluye promocionar a `main` lo acumulado en `dev` (merge commit, no squash).

**Depende de:** nada; no bloquea a nadie.
**Estimación:** 1 día.

---

## Orden de ejecución propuesto

| Días | Persona A | Persona B |
|---|---|---|
| 1 | **T-05** (ADR-006 y ADR-007) — de a dos | idem |
| 2 | T-06 (unidad `h` + seed de mano de obra y equipo) | T-07 (deploy) |
| 3-5 | HU-10 (mano de obra y equipo en recetas) → HU-11 backend | HU-9 (recetas del estudio) |
| 6-7 | HU-11 front | HU-9 front + cierre |
| 8-10 | HU-12 backend (guardar, listar, detalle, cargar) | HU-12 front (pantalla de versiones) |
| 11-12 | QA cruzado, tests de aislamiento, responsive | idem |

Camino crítico: **T-05 → T-06 → HU-10 → HU-11 → HU-12**. HU-9 corre en paralelo y solo comparte con el resto el editor de recetas.

Dos avisos sobre este plan:

- **HU-12 va última porque congela lo que calculan las demás.** Si se implementa antes que HU-10, las primeras versiones guardadas no tienen mano de obra ni equipo y el formato del ítem congelado cambia a mitad de sprint.
- Si el sprint se aprieta, lo que se suelta es **"Cargar esta versión"** de HU-12, no el guardado: guardar e inmutabilidad es lo que pide la cátedra; volver a una versión vieja es lo que agregamos nosotros.

### Dónde estamos

*Se completa a medida que avanza el sprint, como en el Sprint 1.*

**2026-09-25.** **T-05 terminada** (ADR-006 y ADR-007, PR #22). **T-06 implementada** en `feat/t06-hour-unit-labor-seed`: unidad `h`, `Oficial` (5.500 ARS/h), `Ayudante` (4.600 ARS/h) y `Hormigonera` (3.000 ARS/h), y las horas por m² de las tres recetas sembradas (migración `3d8e1b7a9c24`, que no pisa lo editado por pantalla). Efecto transitorio buscado: hasta HU-10/HU-11, la tabla "Materiales" del cómputo de HU-5 lista también las horas de mano de obra y equipo, porque la query de ADR-003 §2 no filtra por tipo — agruparlas es trabajo de HU-11.

**Queda liberado:** HU-10 (camino crítico). **En paralelo:** HU-9 y T-07.

**2026-09-25 (tarde).** **T-06 terminada** (PR #23). **HU-9 implementada**, back (PR #24, mergeado) y front (`feat/hu9-firm-recipes-front`): recetas del estudio en la pantalla Catálogo, con origen visible y filtro, el editor de HU-8 reusado y la receta propia ofrecida en el selector del cómputo. Se precisó ADR-006 al implementar: las rutas van bajo `/firms/{id}/catalog/recipes`, una receta ajena en el cómputo da 409, y el soporte no alcanza recetas de estudio. ADR-006 pasa a **Aceptada**.

**Queda:** HU-10 → HU-11 → HU-12 (camino crítico) y T-07.

**2026-10-01.** **T-07 terminada** (PR #28, `dev` promovido a `main`) y **HU-10 terminada** (PR #26). **HU-11 implementada**, back (`feat/hu11-project-budget`) y front (`feat/hu11-project-budget-front`): `GET /firms/{id}/projects/{id}/budget` con los tres grupos en orden fijo, subtotal por grupo y total general, y la sección "Presupuesto" como una tab más de la obra.

Dos cosas que se precisaron al implementar:

- **Endpoint propio y no un `/takeoff` más rico**, porque el permiso es distinto: el cómputo admite al `client` con los costos en `null`, y el presupuesto tiene que negarle la entrada (403, no 404 — ya puede ver la obra). Además HU-12 cuelga `/budget/versions` de acá.
- **El efecto transitorio de T-06 se resolvió agrupando y no filtrando.** La idea era filtrar la tabla "Materiales" del cómputo a `type = 'material'`, pero HU-10 pide que *el `client` vea las horas y no los costos*: si HU-11 se las saca al cómputo, el cliente —que no entra al presupuesto— no las ve en ninguna pantalla. Las filas de `/takeoff` ahora llevan su `type` y el cómputo las muestra en tres grupos bajo el título "Qué necesita la obra".

**Queda:** HU-12 (camino crítico).

**2026-10-01 (tarde).** **HU-11 terminada** (PRs #29 y #30, mergeados a `dev`). **HU-12 implementada** en tres ramas: esquema (`feat/hu12-budget-versions-schema`), backend (`feat/hu12-budget-versions-back`) y front (`feat/hu12-budget-versions-front`). Las tres tablas de ADR-007, el permiso `project.budget.manage`, las cuatro rutas y la sección de versiones dentro del presupuesto. ADR-007 pasa a **Aceptada**.

Tres cosas que se precisaron al implementar:

- **La inmutabilidad se sostiene por topología, no por un chequeo.** No hay `PUT`, `PATCH` ni `DELETE` bajo `/budget/versions`, y el test que lo cuida compara el conjunto exacto de métodos del prefijo contra los cuatro que existen. Una regla que se sostiene por ausencia de código es justo la que vuelve sola.
- **`load_version` reusa `add_line` de HU-5** en vez de repetir la validación de recetas, y atrapa su rechazo en lugar de propagarlo: una receta dada de baja no aborta la carga, queda afuera y se reporta. De yapa, la regla de ADR-006 sobre recetas de otro estudio vale al cargar sin código nuevo.
- **Las versiones no son una quinta tab.** Viven bajo `budget/versions`, con un link desde el Presupuesto: una tab más a 375px cuesta más de lo que explica, y así la tab Presupuesto queda seleccionada mientras se lee una versión.

**Queda:** nada del alcance del sprint. Falta cerrar la Definition of Done de HU-11 y HU-12: promoción `dev → main` y verificación en Azure.

**2026-09-30.** **T-07 implementada** en `chore/t07-deploy-azure` ([ADR-008](../adr/0008-azure-deploy.md)). El deploy es en Azure y no en Render/Vercel, porque los planes gratis de Render y Neon ya estaban ocupados: backend en Container Apps, base en PostgreSQL Flexible Server y frontend en Static Web Apps, todo con costo USD 0. El ambiente ya está andando con las 11 migraciones y el seed demo, este último con una contraseña propia del ambiente. `.github/workflows/deploy.yml` deploya cada push a `main`. T-07 se cierra con la promoción `dev → main` (merge commit), que además es la primera corrida del workflow.

**2026-10-01 (cierre).** **Sprint 2 promovido a `main`** (PR #34, merge commit) y deployado: la corrida de `deploy.yml` terminó bien. No queda nada del alcance del sprint sin mergear.

**Queda:** la verificación a mano de HU-11 y HU-12 en el ambiente de Azure, que es el último punto de su Definition of Done. El Sprint 3 está en [sprint-3.md](sprint-3.md).
