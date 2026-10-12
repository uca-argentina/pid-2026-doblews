# ADR-009: Planificación de la obra — tareas, dependencias y fechas calculadas

**Estado:** Propuesta
**Fecha:** 2026-10-07
**Contexto:** Modelo de datos y reglas de cálculo para planificar una obra. Desbloquea HU-13 y HU-14 del Sprint 3 y deja definido sobre qué se apoyan HU-15, HU-16 y HU-19. Precisa lo que [ADR-001](0001-stack.md) anticipó sobre el camino crítico.

---

## Contexto

### Qué pide la cátedra

> Dividir la obra en rubros y tareas. Cada tarea tiene responsable, fechas, duración estimada, costo y estado: pendiente, en curso, pausada o finalizada.
> Permitir dependencias entre tareas. Una tarea no puede iniciarse si sus predecesoras obligatorias no finalizaron.

Hasta ahora una obra no tiene planificación: tiene equipo (`project_member`), cómputo (`project_recipe`) y versiones del presupuesto (`budget_version`). Ver [der.md](../der.md).

### Qué decidimos hacer además de lo pedido

El pedido se cumple con fechas cargadas a mano y dependencias que solo bloquean. Decidimos ir más lejos: **las fechas las calcula el sistema** a partir de las duraciones y las dependencias. El arquitecto carga cada tarea con lo que lleva y con qué tiene que estar terminado antes; cuándo empieza, cuándo termina y cuándo termina la obra salen solos, y se corren solos cuando algo se atrasa.

Eso mete en el sprint el camino crítico, que ADR-001 ya había previsto: *"se resuelve con un ordenamiento topológico sobre las tablas relacionales, sin necesidad de una base de grafos para el volumen de tareas esperado en una obra"*.

### Qué restringe la decisión

- Las convenciones de [modelo-datos-sprint-1.md](../modelo-datos-sprint-1.md) §3: `firm_id`, baja lógica, `VARCHAR` + `CHECK`, `DATE` para fechas de calendario, FK compuesta para invariantes entre tablas.
- [ADR-002](0002-authorization-model.md): permisos y nunca roles; obra ajena → 404.
- `project_member` **se borra de verdad** al sacar a alguien del equipo (ADR-002 §11.3): no tiene `is_active`.
- El costo de una obra sale hoy de un solo lugar, el cómputo a precio vigente (ADR-003, ADR-005 §5). No queremos un segundo número de costo que pueda contradecirlo.

---

## Decisión

### 1. Dos tablas nuevas y una columna en el cómputo

```mermaid
erDiagram
    project ||--o{ project_task : "project_id, firm_id"
    firm_member |o--o{ project_task : "firm_id, assignee_account_id"
    project_task ||--o{ project_task_dependency : "predecessor_id, project_id"
    project_task ||--o{ project_task_dependency : "successor_id, project_id"
    project_task |o--o{ project_recipe : "task_id, project_id"

    project_task {
        bigint id PK
        bigint project_id FK
        bigint firm_id FK
        varchar(150) name
        text description "NULL"
        integer estimated_duration_days
        date not_before_date "NULL"
        varchar(20) status
        bigint assignee_account_id FK "NULL"
        date actual_start_date "NULL"
        date actual_end_date "NULL"
        boolean is_active
        timestamptz created_at
        timestamptz updated_at
    }
    project_task_dependency {
        bigint predecessor_id PK, FK
        bigint successor_id PK, FK
        bigint project_id FK
    }
    project_recipe {
        bigint task_id FK "NULL · columna nueva"
    }
```

**`project_task`** — una tarea de una obra.

| Regla | Cómo la sostiene el esquema |
|---|---|
| La tarea es de una obra de ese estudio | FK compuesta `(project_id, firm_id) → project (id, firm_id)`, igual que `project_recipe` |
| El responsable es del mismo estudio | FK compuesta `(firm_id, assignee_account_id) → firm_member (firm_id, account_id)` |
| La duración es positiva | `CHECK (estimated_duration_days > 0)` |
| El estado es uno de cuatro | `CHECK (status IN ('pending', 'in_progress', 'paused', 'finished'))`, por defecto `'pending'` |
| Una tarea pendiente no tiene fechas reales | `CHECK (status <> 'pending' OR actual_start_date IS NULL)` |
| Una tarea que arrancó tiene inicio real | `CHECK (status = 'pending' OR actual_start_date IS NOT NULL)` |
| Solo una finalizada tiene fin real, y siempre lo tiene | `CHECK ((status = 'finished') = (actual_end_date IS NOT NULL))` |
| El fin real no es anterior al inicio real | `CHECK (actual_end_date >= actual_start_date)` |
| Nombre único entre las tareas activas de la obra | Índice único parcial `(project_id, lower(name)) WHERE is_active` (modelo-datos §3.4: es una etiqueta) |
| Una dependencia solo puede unir tareas de la misma obra | `UNIQUE (id, project_id)`, para que `project_task_dependency` y `project_recipe` tengan a qué apuntar (modelo-datos §3.8) |

**`project_task_dependency`** — "la sucesora no puede empezar hasta que termine la predecesora".

Es un vínculo puro y no una entidad, así que sigue a `recipe_resource`: sin `is_active`, sin timestamps, y se borra de verdad al quitarla.

| Regla | Cómo la sostiene el esquema |
|---|---|
| No se repite una dependencia | PK `(predecessor_id, successor_id)` |
| Las dos tareas son de la misma obra | Dos FK compuestas, `(predecessor_id, project_id)` y `(successor_id, project_id)`, contra `project_task (id, project_id)` |
| Una tarea no depende de sí misma | `CHECK (predecessor_id <> successor_id)` |

Índice en `successor_id`: "¿de qué depende esta tarea?" es la consulta del bloqueo.

**`project_recipe.task_id`** — nullable. Una línea de cómputo se asigna **a lo sumo a una tarea**, o queda sin asignar. FK compuesta `(task_id, project_id) → project_task (id, project_id)`: una línea no puede asignarse a una tarea de otra obra.

### 2. Qué se guarda y qué se calcula

| Dato | Origen |
|---|---|
| Nombre, descripción, duración estimada, "no antes de", responsable | Lo carga el usuario |
| Estado | Lo cambia el usuario, por las transiciones de §5 |
| Inicio y fin **reales** | Los registra el cambio de estado; se pueden corregir |
| Inicio y fin **previstos**, holgura, si es crítica | **Se calculan al leer. No hay columna** |
| Fin previsto de la obra | Se calcula: el fin más tardío entre sus tareas |
| Costo de la tarea | Se calcula: suma de sus líneas de cómputo a precio vigente |

**Las fechas previstas no se guardan.** Dependen del día de hoy (§4), así que una columna quedaría vieja cada medianoche sin que nadie escribiera nada. El cálculo recorre las tareas de una obra en memoria: son decenas o pocos cientos, y es más barato recalcular que invalidar.

Las "fechas" que pide la cátedra son, entonces, cuatro: dos previstas (calculadas) y dos reales (registradas).

### 3. Las dependencias

- **Toda dependencia es obligatoria.** El pedido dice "predecesoras obligatorias"; lo leemos como "las predecesoras, que son obligatorias". Si una tarea no tiene que esperar a otra, no se conecta. No hay columna para distinguirlas.
- **Un solo tipo: fin → inicio.** La sucesora empieza el día hábil siguiente al fin de la predecesora. Sin días de espera entre tareas: un fraguado o una entrega se cargan como una tarea propia, que además queda a la vista en el Gantt.
- **Sin ciclos.** Al agregar `A → B` se rechaza si ya existe un camino de `B` a `A`.
- **Se editan desde la sucesora.** El formulario de la tarea manda la lista completa de sus predecesoras, que reemplaza a la anterior; el ciclo se busca con las aristas nuevas, y el rechazo nombra el ciclo entero.

### 4. Cómo se calculan las fechas

Días **hábiles de lunes a viernes**, sin feriados. Una función de calendario única, usada por este cálculo, por el avance planificado (HU-16) y por la proyección mensual (HU-19).

**Recorrido hacia adelante**, en orden topológico:

| Estado de la tarea | Inicio | Fin |
|---|---|---|
| Finalizada | El real | El real |
| En curso o pausada | El real | El más tardío entre *inicio real + duración* y **hoy** |
| Pendiente | El más tardío entre: inicio de la obra, su "no antes de", el día hábil siguiente al fin de su última predecesora, y **hoy** | *Inicio + duración* |

Tres consecuencias de esa tabla:

- **Lo real reemplaza a lo previsto.** En cuanto una tarea arranca o termina, las que dependen se calculan desde lo que pasó.
- **Nada previsto queda en el pasado.** Una tarea en curso que ya debería haber terminado se da por terminada "no antes de hoy", y una pendiente que ya debería haber arrancado, lo mismo. Así un atraso corre las fechas siguientes día a día sin que nadie lo cargue.
- **"Pausada" se calcula igual que "en curso".** Mientras no termina, empuja.

El **inicio de la obra** es `project.estimated_start_date`, que ya existe y es opcional. Sin ella no se calcula: la sección pide cargarla.

**Recorrido hacia atrás**, desde el fin previsto de la obra: da para cada tarea no finalizada su **holgura** en días hábiles (cuánto puede atrasarse sin mover el fin de la obra). Una tarea con holgura cero es **crítica**.

Precisiones que salieron al implementar (HU-14):

- **Fin inclusivo.** Una tarea de *n* días que empieza el día *d* ocupa *d* y los *n − 1* hábiles siguientes; su sucesora empieza el hábil siguiente al fin.
- **Fines de semana.** Un inicio que cae sábado o domingo (el de la obra, un "no antes de") se corre al lunes. "Hoy", como piso, es el primer día hábil desde hoy: un sábado no se planifica nada para el fin de semana. Las fechas reales se respetan como se cargaron.
- **Solo las sucesoras pendientes limitan hacia atrás.** Una sucesora que ya arrancó ya no espera a su predecesora (es el caso de reabrir, §5), así que no le quita holgura.
- **Sin fecha de inicio no hay cronograma**: ninguna tarea tiene fechas previstas ni holgura, y la planificación pide cargarla.

El porcentaje de avance **no entra** en este cálculo.

### 5. Estados y transiciones

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> in_progress : iniciar
    in_progress --> paused : pausar
    paused --> in_progress : reanudar
    in_progress --> finished : finalizar
    finished --> in_progress : reabrir
    in_progress --> pending : deshacer inicio
```

| Transición | Efecto |
|---|---|
| Iniciar | Registra `actual_start_date` (hoy, corregible). **Se rechaza si alguna predecesora activa no está finalizada**, y el rechazo dice cuáles |
| Finalizar | Registra `actual_end_date` (hoy, corregible) |
| Reabrir | Borra `actual_end_date` |
| Deshacer inicio | Borra `actual_start_date` |
| Cualquier otra | Se rechaza |

**El bloqueo se chequea al iniciar, no es un invariante permanente.** Reabrir una tarea cuyas sucesoras ya arrancaron **se permite**, con una confirmación que las lista. El retrabajo existe y lo que ya se hizo no se deshace; las sucesoras con inicio real no se mueven, y las pendientes se recalculan solas.

### 6. Responsable

Un integrante del equipo de la obra **que pueda gestionar sus tareas**, opcional. Se guarda contra **`firm_member`** y no contra `project_member`, porque `project_member` se borra de verdad: una FK ahí impediría sacar del equipo a quien terminó tareas, o perdería quién las hizo.

- Al **asignar**, el servicio exige que la persona tenga `project.task.manage` en la obra: hoy, `lead` y `collaborator` (§9). La regla es un permiso y no una lista de roles (ADR-002), y garantiza que el responsable pueda cambiar el estado de su propia tarea. Queda afuera el `client`.
- La regla se chequea **al asignar y no después**: a quien le cambian el rol dentro de la obra conserva las tareas que ya tenía.
- Al **salir del equipo**, sus tareas no finalizadas quedan sin responsable; las finalizadas lo conservan.

### 7. Baja de una tarea

Baja lógica, en cualquier estado, con confirmación. En la misma transacción:

- Sus dependencias se **borran**, en las dos direcciones. Las sucesoras dejan de estar bloqueadas por ella; la confirmación las lista.
- Sus líneas de cómputo vuelven a quedar **sin asignar**. Nunca se dan de baja por esto.

### 8. Costo

El costo de una tarea es la suma del costo de sus líneas de cómputo, con el mismo cálculo y los mismos precios vigentes del presupuesto de HU-11. Una tarea sin líneas cuesta cero.

Las líneas sin asignar siguen contando en el presupuesto de la obra. En la planificación aparecen como un total "sin asignar a ninguna tarea".

**Redondeo.** El costo de cada tarea y el importe sin asignar se redondean a dos decimales cada uno, y el total de la planificación es la suma de esos importes ya redondeados: lo que se ve en la pantalla siempre cierra. El presupuesto de HU-11 redondea por recurso y no por tarea, así que los dos totales pueden diferir en centavos. Es el mismo criterio de HU-5 y HU-11 (cada pantalla suma lo que muestra), aplicado a otra forma de agrupar las mismas líneas.

> **Precisado el 2026-10-09.** La planificación ya no muestra ese total: el de la obra se ve una sola vez, en el cómputo, y la planificación muestra el costo de cada tarea y el importe sin asignar. `GET /tasks` lo sigue devolviendo en `total_cost`, calculado como dice este párrafo.

### 9. Permisos

| Ámbito | Código | Roles |
|---|---|---|
| `project` | `project.task.view` | `lead`, `collaborator`, `client` |
| `project` | `project.task.manage` | `lead`, `collaborator` |

Es el mismo reparto que `project.recipe.view` / `project.recipe.manage` (ADR-003 §8). El `owner` lee por `project.view_all`. El costo de las tareas exige además `project.cost.view`, así que **el `client` ve la planificación sin importes**.

### 10. Reglas que el esquema no puede garantizar

Van en el servicio, cada una con su test:

1. **No hay ciclos de dependencias.** Además, escribir una dependencia toma un bloqueo sobre la fila de la obra, para que dos altas simultáneas no cierren un ciclo entre las dos.
2. **Una tarea no se inicia con predecesoras sin finalizar.**
3. **Solo se permiten las transiciones de §5.**
4. **El responsable tiene `project.task.manage` en la obra** al momento de asignarlo.
5. **Dar de baja una tarea** borra sus dependencias y desasigna sus líneas.
6. **Sacar a alguien del equipo** desasigna sus tareas no finalizadas.
7. **Una dependencia no une tareas dadas de baja**, y una línea de cómputo no se asigna a una.

### 11. Dónde vive el cálculo

Un módulo propio, de funciones puras sobre tareas y aristas ya leídas de la base: detección de ciclos, orden topológico, recorridos hacia adelante y hacia atrás, y el calendario de días hábiles. Sin SQL adentro, así se prueba sin base.

Es también la costura para la extensión de §Consecuencias: el resto de la aplicación le pide "las fechas de esta obra" y no sabe cómo se obtienen.

### 12. La vista en el tiempo

Decidido el 2026-10-10, al arrancar HU-15. No agrega modelo ni endpoints: la vista dibuja lo que `GET /tasks` ya devuelve.

| Pregunta | Decisión | Por qué |
|---|---|---|
| Calendario o Gantt | **Gantt**: una fila por tarea, la barra de su inicio a su fin | Es donde se leen la duración, la superposición y el camino crítico, que es lo que calcula §4 |
| Con qué componente | **Propio, con Mantine.** Sin dependencias nuevas | La vista es de lectura, y lo que una librería de Gantt ahorra es el arrastre. Queda aislado en un componente que recibe las tareas, así que se puede reemplazar |
| Qué se puede hacer | **Es de lectura.** Elegir una tarea abre su detalle, y desde ahí la edita quien tiene `project.task.manage` | Las fechas previstas no se editan (§2): se cambia lo que las produce, y eso ya tiene su formulario. Al guardar, las barras se reacomodan solas |
| Las dependencias | **No se dibujan.** Se leen en el detalle de la tarea | Verlas de un vistazo es el trabajo de una vista de grafo, que queda como extensión |
| Escalas | Días, semanas y meses | |
| 375px | **Diferido.** En pantallas chicas la planificación muestra el listado en tarjetas y no ofrece el Gantt | Alcance del sprint. Un Gantt es horizontal por naturaleza y resolverlo bien en un celular es un trabajo aparte |

La barra usa el color del estado de la tarea, el mismo del listado, y distingue lo que ya pasó de lo previsto. Las críticas van destacadas, y están marcados el día de hoy y el fin previsto de la obra.

### 13. Avance y línea base

Decidido el 2026-10-12, al arrancar HU-16. No agrega tablas ni permisos: son columnas en `project_task` y en `project`, y escribirlas exige `project.task.manage` (§9).

**Qué se guarda**

| Tabla | Columna | Regla en el esquema |
|---|---|---|
| `project_task` | `progress_percent INTEGER NOT NULL DEFAULT 0` | `CHECK (progress_percent BETWEEN 0 AND 100)` |
| | | Una pendiente está en cero: `CHECK (status <> 'pending' OR progress_percent = 0)` |
| | | Una finalizada está al cien: `CHECK (status <> 'finished' OR progress_percent = 100)` |
| `project_task` | `baseline_start_date`, `baseline_end_date`, `DATE NULL` | Las dos o ninguna; el fin no es anterior al inicio |
| `project` | `baseline_set_on`, `baseline_end_date`, `DATE NULL` | Las dos o ninguna |

El avance **planificado**, la diferencia y el avance de la obra **se calculan al leer**, como las fechas previstas (§2): dependen del día de hoy.

**La línea base.** Las fechas previstas se corren solas con cada atraso (§4), así que no sirven de referencia: una tarea atrasada siempre "debería terminar hoy". **"Fijar planificación"** copia el inicio y el fin previstos de cada tarea activa a sus dos columnas, y a la obra el día en que se fijó y su fin previsto de ese momento. La comparación es contra esa copia.

- **Volver a fijar reemplaza** la anterior, en todas las tareas. No se guarda historial.
- Sin fecha de inicio o sin tareas no hay qué fijar, y se rechaza.
- Una tarea **creada después de fijar** no tiene línea base: aparece marcada y no entra en la comparación hasta que se vuelva a fijar.
- La obra guarda **su propio fin fijado** en vez de calcularlo como el máximo de sus tareas, que cambiaría al dar de baja una. Es lo que HU-19 compara contra el fin previsto.

**Las decisiones**

| | Pregunta | Decisión | Por qué |
|---|---|---|---|
| D-10 | Avance planificado de una tarea a hoy | **Lineal en días hábiles** sobre el tramo fijado: 0% antes del inicio, 100% desde el fin, y en el medio los hábiles transcurridos sobre los del tramo | Supone un ritmo parejo, que es lo único que se puede suponer sin más datos, y usa el calendario de §4 |
| D-11 | Cuánto pesa cada tarea en el avance de la obra | **Su duración estimada** | Toda tarea tiene una, así que siempre hay número; lo puede ver el `client`, porque no sale de costos; y no se mueve cuando cambian los precios |
| D-12 | Avance y estado | **El estado manda.** Pendiente es 0 y finalizada es 100; en curso o pausada se carga de 0 a 100 | Los dos CHECK de arriba. Es la incoherencia que la historia pide evitar |
| D-13 | Historial de los avances | **Solo el valor actual** | Nada del sprint lo consume: HU-16 y HU-19 muestran el avance a hoy |

Cómo se mueve el avance con las transiciones de §5:

| Transición | Avance |
|---|---|
| Finalizar | Pasa a 100 |
| Deshacer inicio | Vuelve a 0 |
| Reabrir | **Conserva el valor**, y se corrige a mano |
| Iniciar, pausar, reanudar | No lo tocan |

**Llegar al 100% no finaliza la tarea.** Finalizar registra una fecha real y tiene su confirmación; que ocurra como efecto de escribir un número se la saltearía. Registrar avance en una tarea pendiente o finalizada se rechaza, diciendo qué hacer: iniciarla o reabrirla.

**Precisiones**

- **"A hoy" incluye el día de hoy**, como el fin inclusivo de §4: el día del fin fijado, el planificado ya es 100%.
- **El denominador es el tramo fijado** y no la duración estimada, que pudo editarse después de fijar.
- **"En fecha" tiene una tolerancia de 5 puntos.** La diferencia es *real − planificado*: por debajo de −5 la tarea viene atrasada, por encima de +5 adelantada, y en el medio en fecha. Con diferencia exacta casi ninguna estaría en fecha.
- **El avance de la obra** es el promedio del real y el del planificado, ponderados por duración, **solo sobre las tareas con línea base**. Cada uno se redondea a entero y la diferencia se calcula sobre los dos ya redondeados, para que lo que se ve en pantalla cierre (el criterio de §8).
- **El avance no entra en el cálculo de fechas** (§4): esas dependen solo de duraciones, dependencias y fechas reales.

El cálculo vive en un módulo propio de funciones puras, al lado del de §11 y sobre su calendario.

**En pantalla**

Precisado el 2026-10-12, después de revisar una primera versión que mostraba todo dentro de la planificación.

- **El avance tiene su propia sección de la obra, "Avance"**, y no es parte de "Planificación". Son dos preguntas: qué se hace y cuándo, y cómo venimos. La lista de tareas y el Gantt (§12) ya llevan lo que pueden llevar; ahí no se muestra ni se carga avance.
- **En pantalla, "atrasada" es una tarea cuyo fin fijado ya pasó y que no está finalizada.** No es la situación por tolerancia de arriba. Una tarea a mitad de su tramo con poco avance está por debajo de un ritmo parejo que nadie le prometió; mostrarla como atrasada, y con ella a la obra, se leía como una alarma falsa. Una fecha vencida no se discute.
- Para lo demás, la pantalla muestra **los dos números lado a lado**, el real y el planificado, sin veredicto. La obra tampoco lleva etiqueta: muestra sus dos porcentajes y cuántas tareas están atrasadas.
- **La diferencia y la situación por tolerancia se siguen calculando** y viajan en la respuesta, sin mostrarse. Quedan para el dashboard (HU-19), que decide si las usa.

---

## Consecuencias

**Se desbloquea:**

- HU-13 (tareas) y HU-14 (dependencias y fechas previstas).
- HU-15 tiene qué dibujar: fechas previstas y reales, estado, críticas y aristas.
- HU-19 puede proyectar el gasto por mes: cada tarea tiene costo y fechas.

**Compromisos que asumimos:**

- El sprint incluye **más de lo que pide la cátedra**: fechas calculadas, propagación de atrasos y camino crítico. HU-14 crece.
- `project.estimated_start_date` pasa a ser necesaria para planificar. No se vuelve `NOT NULL`: una obra puede existir sin planificación.
- Las fechas previstas **cambian solas con el paso de los días**. Es lo buscado, pero obliga a tener una referencia fija para comparar: la línea base de §13.
- `project_recipe` gana una columna y una regla: HU-5 tiene que ofrecer la asignación a una tarea.

**Queda pendiente de decidir, y con qué historia:**

| Tema | Se decide al arrancar |
|---|---|
| **Rubros.** Fuera por ahora: el pedido los menciona una sola vez y se consulta con la cátedra. Si entran, es una tabla y una FK nullable en `project_task` | Respuesta de la cátedra |
| **Versiones del presupuesto y asignación a tareas.** Cargar una versión (HU-12) da de baja las líneas del cómputo y crea otras nuevas, así que hoy **las líneas cargadas quedan sin asignar** y la pantalla lo avisa. Previsto: que `budget_version_line` guarde `task_id` y la carga lo restaure si la tarea sigue activa | HU-19 (D-17) |

**Extensiones previstas, no descartadas:**

| Tema | Se revisa cuando |
|---|---|
| **Base de grafos (Neo4j) para los cálculos de red.** Fue propuesta del equipo y bien vista por la cátedra. Se suma como **proyección**: Postgres sigue siendo la fuente de verdad de tareas y dependencias, el grafo se carga desde ahí y reemplaza la implementación del módulo de §11. No requiere migrar datos ni cambiar estas tablas | El módulo de planificación esté funcionando |
| Días de espera entre tareas, y los otros tipos de dependencia | La tarea "de espera" resulte incómoda |
| Días hábiles configurables por obra, y feriados | Una obra trabaje sábados, o las fechas calculadas fallen por feriados |
| Simulación de atrasos ("qué pasa si") | Después del Gantt |
| Historial de líneas base | Haga falta ver cómo cambió el plan |
| **Historial de avances y curva S.** Una tabla con cada registro, su fecha y quién lo cargó, de donde sale la curva de avance en el tiempo. `progress_percent` pasaría a ser el último registro | Haga falta ver cómo evolucionó el avance y no solo dónde está |
| Avance dibujado sobre las barras del Gantt | Después de HU-16 |
| **Vista de grafo de las dependencias.** La red de tareas dibujada como nodos y aristas. Es donde las dependencias se ven de un vistazo, y por eso el Gantt no las dibuja (§12) | Después del Gantt |
| El Gantt a 375px | Después de HU-15, en su propia rama |
| Arrastrar tareas en el Gantt. Mover una barra escribiría el "no antes de" y estirarla la duración; el resto de los movimientos no tiene qué escribir | La edición desde el detalle resulte incómoda |

---

## Alternativas descartadas

**Fechas cargadas a mano, con las dependencias solo bloqueando.** Cumple el pedido y es bastante menos trabajo. Descartada porque el valor de cargar dependencias está en que el plan se mueva solo: con fechas a mano, cada atraso obliga a corregir una por una las tareas siguientes.

**Guardar las fechas previstas en columnas.** Lecturas más baratas. Descartada porque dependen de la fecha de hoy: quedarían viejas cada día sin ninguna escritura, y habría que recalcular igual.

**Base de grafos como fuente de verdad de las dependencias.** El modelo se parece más al problema y los recorridos se escriben en una línea. Descartada **para este sprint** por el corte: el bloqueo cruza el estado de la tarea con sus aristas, y con dos bases eso son dos escrituras sin transacción común. Con el volumen de una obra tampoco hay ganancia de rendimiento. Queda como extensión, en el rol de proyección.

**Dependencias obligatorias y no obligatorias.** Lectura más literal del pedido. Descartada porque una dependencia que no bloquea no dice nada: si no hay que esperar, no se conecta.

**Responsable con FK a `project_member`.** Dejaría en el esquema que el responsable integra la obra. Descartada porque `project_member` se borra: habría que elegir entre no poder sacar a alguien del equipo o perder quién hizo cada tarea.

**Cualquier integrante de la obra como responsable.** Lectura literal de "integrantes del equipo". Descartada porque incluía al `client`, que no puede cambiar el estado de la tarea de la que sería responsable. Limitarlo al rol de estudio `architect` tampoco servía: deja afuera al `owner` que es `lead` de su obra.

**Reasignar por coincidencia al cargar una versión.** Cada línea cargada heredaría la tarea de la línea anterior con la misma receta, cantidad y nota. Descartada porque es una adivinanza: cuando la versión difiere del borrador no coincide, y falla sin decir en cuál.

**Costo de la tarea cargado a mano.** Más simple y sirve para tareas sin cómputo. Descartada porque crea un segundo número de costo de la obra, sin nada que lo haga coincidir con el presupuesto.

**Una línea de cómputo repartida entre varias tareas.** Más fiel cuando un ítem se ejecuta en etapas. Descartada por la tabla intermedia y la pantalla de reparto: lo mismo se logra cargando dos líneas.

**Bloquear la reapertura de una tarea con sucesoras iniciadas.** Mantendría siempre que "si arrancó, sus predecesoras terminaron". Descartada porque registrar un retrabajo obligaría a borrar fechas reales de trabajo ya hecho.

**Días corridos.** Sin calendario que mantener. Descartada porque con fechas calculadas da resultados que nadie espera: una tarea "de 5 días" terminaría contando el fin de semana.

**Calendario mensual en vez de Gantt.** El pedido admite cualquiera de los dos, y un calendario se adapta mejor a un celular. Descartado porque parte en franjas una tarea de varias semanas, se desborda con tareas en paralelo y casi no deja ver el camino crítico.

**Una librería de Gantt** (`@svar-ui/react-gantt`, `frappe-gantt`). Traen hechas las escalas, las flechas y el arrastre. Descartada porque de eso la vista solo usa las escalas: lo demás hay que apagarlo, y a cambio hay que adaptar un estilo ajeno al de la aplicación. `frappe-gantt` además no es un componente de React.

**Arrastrar las tareas en el Gantt.** Descartado para HU-15 porque las fechas previstas se calculan: cada gesto habría que traducirlo a un dato de entrada, mover una tarea hacia atrás no tiene traducción, y como el cronograma se recalcula la barra no siempre queda donde se soltó. Queda como extensión.

**Flechas de dependencia sobre el Gantt.** Es lo habitual. Descartadas porque con muchas tareas se enmarañan y son la parte más cara del componente; las dependencias ya se leen en el detalle de cada tarea, y la vista pensada para mostrarlas es el grafo.

**Comparar el avance contra las fechas previstas, sin línea base.** Ahorra las cuatro columnas y el botón. Descartada porque las previstas se corren a hoy con cada atraso: una tarea en curso y vencida tendría siempre un planificado de 100%, y una pendiente atrasada, de 0%. La comparación mediría contra un plan que se acomoda al atraso.

**Avance planificado "todo al final"** (0% hasta el fin fijado, 100% desde ahí). Trivial y conservador. Descartado porque una tarea larga en curso no aparece atrasada hasta que vence: la comparación calla justo cuando más sirve.

**Avance planificado 50/50** (50% al llegar el inicio fijado, 100% al fin). Es una regla clásica de valor ganado. Descartada porque los saltos se ven arbitrarios en pantalla y no hay cómo explicarlos a quien mira su obra.

**Pesar cada tarea por su costo.** Es el valor ganado de manual. Descartado porque una tarea sin líneas de cómputo pesaría cero y una obra sin líneas asignadas no tendría avance; porque el porcentaje se movería con cada actualización de precios (§8); y porque al `client` habría que mostrarle un número derivado de costos que no puede ver (§9).

**Todas las tareas con el mismo peso.** Lo más fácil de explicar. Descartado porque una tarea de un día pesaría lo mismo que una de cuarenta.

**Que llegar al 100% finalice la tarea.** Un paso menos. Descartado porque sería un cambio de estado como efecto secundario de un número: registraría la fecha real de fin sin preguntarla, salteando la confirmación de §5.

**Avance independiente del estado.** Lo más simple: un número suelto que ninguna transición toca. Descartado porque permite una tarea finalizada al 40% o una pendiente al 60%.

**Mostrar el avance dentro de la planificación** (una columna en la lista y un bloque arriba). Fue la primera versión. Descartada porque cargaba la pantalla del día a día con una pregunta que no es la suya, y repetía en dos lugares lo mismo.

**Etiquetar en pantalla cada tarea y la obra como atrasada, en fecha o adelantada, por tolerancia.** Es lo que calcula el backend. Descartado en pantalla porque marcaba como atrasada una obra en la que ninguna tarea había llegado a su fecha de fin.

**Guardar el historial de los avances.** Deja lista la curva S. Descartado para este sprint porque es una tabla nueva con su pantalla y nada de lo pedido la consume. Queda como extensión.

---

## Referencias

- [ADR-001](0001-stack.md) — PostgreSQL, y el camino crítico por orden topológico.
- [ADR-002](0002-authorization-model.md) §7 y §11.3 — permisos por rol, y por qué `project_member` no tiene `is_active`.
- [ADR-003](0003-recipe-catalog.md) §8 — el reparto de permisos que este copia.
- [ADR-005](0005-catalog-administration.md) §5 — precio vigente.
- [modelo-datos-sprint-1.md](../modelo-datos-sprint-1.md) §3 — convenciones.
- [sprint-3.md](../historias/sprint-3.md) — HU-13 a HU-16 y HU-19.
