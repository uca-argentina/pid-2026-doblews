# ADR-005: Administración del catálogo del sistema por pantalla

**Estado:** Aceptada
**Fecha:** 2026-09-12 (aceptada 2026-09-15, al implementarse el backend de HU-8)
**Contexto:** Cómo crece y se mantiene el catálogo de recursos y recetas. Reemplaza la parte de [ADR-003 §1](0003-recipe-catalog.md) que lo declara de solo lectura en runtime. Motiva la historia HU-8.

## Contexto

[ADR-003](0003-recipe-catalog.md) decidió que el catálogo —recursos y recetas— es **de la plataforma y no de cada estudio**, y que se **siembra por migración**. El párrafo relevante de su §1 dice:

> Los recursos y las recetas se **siembran por migración**, son iguales para todos los estudios y son **de solo lectura en runtime**. Ningún endpoint escribe en ellos.

La primera mitad de esa frase sigue siendo correcta y no se toca: un catálogo por estudio haría que cada uno arrancara con una pantalla en blanco, que es exactamente el trabajo que el producto promete evitar. Lo que esta ADR corrige es la segunda mitad.

### Qué cambió

El catálogo no es un dato que se define una vez. Tiene dos motores de cambio, y los dos son permanentes:

- **Crece.** Van a faltar materiales y recetas, y se van a agregar de a poco, a medida que aparezcan obras que los necesiten. No hay una versión "completa" del catálogo a la cual llegar.
- **Envejece.** El `reference_price` de cada material se desactualiza solo. En un contexto de inflación alta, un precio de hace tres meses no es una aproximación: es un número equivocado, y un cómputo hecho con él da un presupuesto que no sirve.

Con el catálogo cerrado en runtime, **actualizar el precio del cemento es trabajo de desarrollo**: una migración, un pull request, un merge y un deploy. Eso es aceptable para las dos semanas del Sprint 1 y deja de serlo apenas la aplicación tenga un uso real, porque pone a una tarea de negocio —que sabe hacer cualquiera que conozca el rubro— detrás de un ciclo de entrega de software.

### Una señal que ya estaba en el esquema

El propio modelo de ADR-003 §2 lo anticipaba sin decirlo. La tabla `resource` tiene `price_updated_at`, `is_active` y `updated_at`, y esas tres columnas **solo tienen sentido en una tabla que se mantiene**: un catálogo verdaderamente inmutable no necesita saber cuándo cambió un precio ni tener bajas lógicas. El esquema ya estaba preparado; lo que faltaba era la decisión.

### Restricciones

- El Sprint 1 tiene cinco historias pendientes, la habilitadora T-04 y todavía no tiene deploy. Esta decisión **no entra en ese sprint**: se documenta ahora y se implementa después (HU-8).
- El equipo son 2-3 personas. No hay una organización con áreas separadas que justifique roles finos.
- El catálogo es global: un error acá lo ven todos los estudios a la vez. Es la diferencia más importante respecto de cualquier otra pantalla del producto, donde un error afecta a un solo tenant.

## Decisión

### 1. El catálogo se administra en runtime, por pantalla

Recursos y recetas dejan de ser de solo lectura. Hay endpoints que escriben en ellos y una pantalla que los usa.

Lo que **no** cambia, y sigue siendo lo que dice ADR-003:

- el catálogo es **uno solo y global**: no hay catálogo por estudio ni precios por estudio;
- una receta dice qué lleva **1 unidad** de algo, y no hay composición de recetas dentro de recetas;
- el **precio de referencia es único**;
- `unit_of_measure` **sigue cerrado** por migración (HU-0: el catálogo de unidades no tiene ABM, y un metro cuadrado no se edita).

### 2. Lo administra el rol de plataforma `support`

Se agregan permisos de **ámbito plataforma**:

| Permiso | Qué habilita |
|---|---|
| `catalog.manage` | Dar de alta, editar y dar de baja recursos y recetas |

Un solo permiso y no cuatro (`create` / `edit` / `deactivate` / ...) porque no existe ningún rol al que le quepa una parte y no la otra: quien puede crear un material puede corregirle el precio. El día que aparezca esa distinción, partirlo es agregar filas de seed, que es exactamente la propiedad que ADR-002 compró.

**Esto precisa la regla de [ADR-002 §7](0002-authorization-model.md), no la rompe.** Esa sección dice que el `support` "no tiene ni un solo permiso de contenido" y que no debe tenerlo nunca. El motivo que da es concreto: que un bug en la resolución de permisos no se convierta en una fuga de datos entre estudios que compiten. Ese motivo es sobre **el contenido de los estudios** —obras, cómputos, presupuestos—, y sigue vigente sin excepciones. El catálogo no pertenece a ningún estudio, no contiene datos de nadie, y ADR-003 §1 ya dejó dicho que es conocimiento del rubro y no una ventaja competitiva. La regla se lee, entonces: **el soporte no tiene permisos sobre el contenido de los estudios**; el catálogo global es la única cosa de contenido que administra.

La tabla de roles de ADR-002 §7 se actualiza con esta fila.

### 3. Se administran recursos y recetas

- **Recursos** (`resource`): nombre, tipo, unidad de medida, precio de referencia. Es un formulario chato.
- **Recetas** (`recipe` + `recipe_resource`): la cabecera más sus líneas de "este recurso, esta cantidad por unidad". Es maestro-detalle, y es la pantalla más difícil del producto.

Se incluyen las dos aunque la segunda cueste el doble, porque un catálogo donde se pueden cargar materiales pero no las recetas que los usan no resuelve el problema: el material nuevo no se puede computar hasta que alguien escriba una migración, que es el ciclo que esta ADR viene a evitar.

### 4. El seed sigue existiendo, con otro significado

La migración de seed no desaparece: pasa de ser *la* forma de cargar el catálogo a ser su **contenido inicial**. Sigue siendo lo que hace que la aplicación sirva desde el minuto cero, y lo que usan los tests y los ambientes nuevos.

Consecuencia que conviene tener presente: desde el primer alta por pantalla, **el catálogo de un ambiente deja de ser igual al seed**. El seed siembra lo que falta y no pisa lo que ya está.

### 5. El precio es vivo: el cómputo se recalcula

El cómputo de una obra usa **siempre el precio actual**. No se congela el precio en la línea del cómputo ni se guarda historial.

Es la contracara directa del problema que motiva esta ADR: si los precios se actualizan para que los presupuestos sirvan, congelarlos en cada obra haría que la actualización no llegara justamente a las obras que ya están cargadas. El costo que se asume es real y hay que decirlo: **el presupuesto de una obra cambia sin que nadie la haya tocado**.

Se mitiga mostrando de cuándo es el precio, que es el dato que `resource.price_updated_at` ya guarda: la pantalla del cómputo indica que los importes son "precios de referencia al \<fecha\>". Un número viejo con su fecha a la vista es honesto; un número viejo sin fecha es una trampa.

### 6. Las bajas son lógicas y no rompen lo que las usa

- **Un recurso usado por una receta activa no se puede dar de baja.** Se rechaza con 409 y hay que sacarlo de esas recetas primero. Es la misma forma de la regla que HU-2 aplica al `lead` de una obra activa: el sistema no deja que una baja convierta a otra fila en inconsistente.
- **Una receta dada de baja no se ofrece más para cargar**, pero las líneas de cómputo que ya la usan siguen calculando. Borrarla cambiaría el presupuesto de obras ajenas al cambio.
- Nada se borra físicamente, como en todo el proyecto.

### 7. Reglas que la base no puede garantizar

Es el equivalente de [ADR-002 §11](0002-authorization-model.md) para este módulo, y hace falta escribirlo porque las reglas de §6 **se leen como si el esquema las sostuviera, y no lo hace**. Van en la capa de servicio, **cada una con su test**:

1. **Un recurso usado por una receta activa no se puede dar de baja.** Ninguna constraint puede expresarlo: es una condición sobre las filas de otra tabla, no sobre la fila que se está escribiendo. Hoy un `UPDATE resource SET is_active = false` deja recetas activas apuntando a un material de baja, y el cómputo de una obra lo sigue sumando. El índice `ix_recipe_resource_resource_id` existe para que esa verificación sea barata.
2. **Una receta activa tiene al menos una línea.** Mismo motivo: la condición vive en `recipe_resource`. Una receta vacía no da error, da cero materiales, que es la trampa silenciosa que HU-8 declara como criterio de aceptación. La restricción tiene que aplicarse al guardar la receta, no al leerla.
3. **`price_updated_at` se mueve cuando cambia el precio, y solo entonces.** Acá el esquema garantiza la mitad y la capa de servicio la otra: el trigger de `updated_at` deja esa columna quieta —editar el nombre de un material no ensucia la fecha de su precio, y hay un test de esquema que lo prueba—, pero nada obliga a actualizarla cuando el precio sí cambia. Si el `UPDATE` del precio se olvida de tocarla, la pantalla del cómputo miente con una fecha vieja, que es exactamente lo que §5 quiere evitar.

Lo que la base **sí** garantiza sola, desde T-04: que un precio no sea negativo, que una moneda sea un código ISO de tres letras, que un rendimiento y una cantidad computada sean mayores que cero, que dos materiales activos no compartan nombre ni siquiera con otra capitalización, y —vía la FK compuesta contra `project (id, firm_id)`— que una línea de cómputo no pueda apuntar a la obra de otro estudio.

## Consecuencias

**Se desbloquea:**

- El catálogo crece y se corrige sin pasar por un deploy, que es el objetivo entero de esta ADR.
- HU-8 queda definida y se puede estimar.
- El día que haya un cliente real, actualizar precios es una tarea de negocio y no un ticket de desarrollo.

**Compromisos que asumimos:**

- **Los presupuestos cambian retroactivamente** cuando cambia un precio. La pantalla del cómputo tiene que mostrar la fecha del precio.
- **Un error del soporte impacta a todos los estudios a la vez.** Es el precio de tener un catálogo único, y no hay rollback más allá de volver a editar. Mitigado por la baja lógica: nada desaparece.
- **El catálogo de cada ambiente diverge del seed** apenas alguien edita algo por pantalla.
- **No hay auditoría de quién cambió qué.** Solo queda `updated_at`, que lo mantiene el trigger. Con 2-3 personas es tolerable.

**Queda pendiente de revisar, y bajo qué condición:**

| Tema | Se revisa cuando |
|---|---|
| Historial de precios con vigencia | Se necesite reconstruir un presupuesto viejo, o alguien pregunte "¿por qué cambió esta obra?" |
| Congelar el precio en la línea de cómputo | Un estudio necesite presupuestos estables para presentarle a su cliente |
| Auditoría de cambios del catálogo (quién, cuándo, qué) | Administre el catálogo más de una persona |
| Rol `catalog_admin` separado de `support` | El equipo crezca y quien arregla cuentas deje de ser quien sabe de precios de obra |
| Importación por CSV | Cargar a mano se vuelva impracticable — a partir de unas decenas de materiales |
| Recetas propias de cada estudio | Un estudio pida una receta que el catálogo del sistema no cubre (ya anotado en ADR-003) |

## Alternativas descartadas

**Seguir solo con migraciones** (lo que decía ADR-003). Es lo más simple y tiene una ventaja real: todo cambio del catálogo queda versionado y revisado en un pull request. Descartada porque pone cada actualización de precio detrás de un ciclo de deploy, y los precios envejecen en semanas.

**Un rol nuevo `catalog_admin`, separado de `support`.** Conceptualmente más prolijo: quien administra cuentas no es necesariamente quien sabe cuántos ladrillos lleva un metro cuadrado. Descartada por ahora porque no hay ninguna persona real que ocupe ese rol y no el otro; queda anotada arriba con la condición bajo la cual se revisa.

**Administrar solo los materiales y dejar las recetas sembradas.** La mitad del trabajo. Descartada porque un material que no se puede meter en ninguna receta no se puede computar, así que la pantalla resolvería la parte fácil del problema y dejaría intacta la que motiva la ADR.

**Congelar el precio en cada línea de cómputo**, guardándolo al cargarla. Da presupuestos estables y auditables. Descartada por ahora porque anula el efecto de actualizar precios justo donde más importa —las obras ya cargadas— y porque agrega columnas y una operación de "repreciar" que nadie pidió todavía.

**Historial de precios con vigencia.** Es la solución correcta a largo plazo y ya estaba anotada como pendiente en ADR-003. Descartada por tamaño: es una historia entera, no un agregado a esta.

**Abrir el catálogo a los estudios**, para que cada uno cargue lo suyo. Descartada de nuevo, por el mismo motivo por el que ADR-003 la descartó: cada estudio arrancaría con una pantalla en blanco cargando a mano proporciones que son conocimiento público del rubro.

**Borrado físico de recursos y recetas.** Descartada por la regla del equipo —toda baja es lógica— y porque un recurso borrado dejaría recetas apuntando a la nada y cómputos incalculables.

## Fuera de alcance de esta ADR

El ABM de unidades de medida, que sigue cerrado; los precios por estudio y por proveedor; el historial de precios; la importación masiva; la auditoría de cambios; y las recetas propias de cada estudio. Todas están anotadas arriba con la condición bajo la cual se revisan.
