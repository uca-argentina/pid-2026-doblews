# Historias de Usuario — Sprint 1 (MVP)

**Materia:** Proyecto Integral de Desarrollo — UCAio
**Duración del sprint:** 2 semanas
**Equipo:** 2-3 personas (fullstack)

## Decisiones de alcance confirmadas

El modelo de usuarios, roles y permisos está definido en [ADR-002](../adr/0002-authorization-model.md). Esa ADR es la fuente de verdad; si algo de este documento la contradice, gana la ADR.

- La plataforma es **multi-estudio**: varios estudios de arquitectura la usan en paralelo y ninguno ve datos de otro.
- Una persona tiene **una sola cuenta** y puede pertenecer a varios estudios, con un rol distinto en cada uno.
- Hay roles en **tres ámbitos**: `support` (plataforma), `owner` / `architect` / `client` (estudio) y `lead` / `collaborator` / `viewer` / `client` (obra).
- El **cliente** de una obra es un miembro del estudio con rol `client`, asignado a esa obra. No es una columna de `project`.
- Los estudios los da de alta el **soporte**; no hay auto-registro público.
- Cada persona ve únicamente **las obras de las que es miembro**, dentro del estudio en el que está actuando.
- Los endpoints chequean **permisos** (`project.edit`), nunca roles. Recurso ajeno → **404**, nunca 403.
- La moneda de los precios es **ARS fijo**, pero el campo `currency` se modela desde ahora para soportar otras monedas más adelante.
- Todos los ABM usan **baja lógica** (`is_active`), nunca `DELETE` físico.

El modelo del cómputo de materiales está definido en [ADR-003](../adr/0003-recipe-catalog.md), que cierra lo que HU-4 y HU-5 tenían bloqueado:

- El **catálogo de materiales y recetas es del sistema**, no de cada estudio: se siembra por migración, es igual para todos y es de solo lectura. Así la aplicación sirve desde el primer login, sin que nadie cargue proporciones a mano.
- Una **receta** dice qué lleva **1 unidad** de algo ("1 m² de pared de 15cm lleva 60 ladrillos y 0,25 bolsas de cemento"). La obra guarda **qué recetas usa y en qué cantidad**, y de ahí sale el cómputo.
- **No hay composición de componentes dentro de componentes.** Se evaluó, existe en el software del rubro, y se descartó.
- El **precio de referencia es único y global**. Precios por estudio o por proveedor quedan para más adelante.

---

## T-01 — Definir el nombre de la aplicación

Tarea de equipo, no historia de usuario. Timebox: 30 minutos. Bloquea el repo, Figma, el deploy y la presentación — se resuelve antes que cualquier otra cosa.

**Resuelta:** el nombre es **warchitecture** (es el nombre del repo y del proyecto).

---

## HU-0 — Catálogo de unidades de medida

*Habilitadora técnica: chica, pero desbloquea HU-4 y HU-5.*

> Como **sistema**, necesito un catálogo cerrado de unidades de medida para que materiales y componentes se expresen siempre con las mismas unidades y los cómputos futuros sean calculables.

**Criterios de aceptación**

- Existe la tabla `unit_of_measure` con `id`, `code` (m2, m3, ml, u, kg, bolsa, lt), `name`, `abbreviation`.
- Se carga por migración/seed, no por pantalla.
- El catálogo es **global a la plataforma**, no por estudio: un metro cuadrado es un metro cuadrado en todos ([ADR-003](../adr/0003-recipe-catalog.md)).
- Hay un endpoint `GET /units-of-measure` que devuelve la lista.
- En el front, cualquier campo "unidad" es un `<select>` alimentado por ese endpoint. Nunca texto libre.

**Fuera de alcance:** ABM de unidades por pantalla, conversiones entre unidades.
**Depende de:** nada.
**Estimación:** 0,5 día.

---

## HU-1 — Iniciar sesión

> Como **arquitecto**, quiero iniciar sesión con mi email y contraseña para acceder a mis obras y que nadie más vea mi información.

**Criterios de aceptación**

- Con credenciales válidas, el sistema me devuelve un token y me lleva al listado de obras.
- Con credenciales inválidas, veo un mensaje genérico ("Email o contraseña incorrectos"), sin distinguir si el email existe.
- Si intento entrar a una pantalla interna sin sesión, me redirige al login.
- La sesión persiste al recargar la página.
- Hay un botón de cerrar sesión visible en el layout.
- Las contraseñas se guardan hasheadas (bcrypt/argon2), nunca en texto plano.
- Existen por seed un usuario `support` y, por cada estudio semilla, su `owner`, para poder entrar la primera vez.
- Después del login se resuelve **en qué estudio estoy actuando**: si pertenezco a uno solo entro directo; si pertenezco a varios, elijo. El estudio va explícito en la URL, no guardado en la sesión.
- Si no pertenezco a ningún estudio, veo una pantalla que lo explica — no un listado vacío ni un error.
- Los permisos **no viajan dentro del token**: se resuelven contra la base en cada request, para que una baja o un cambio de rol tengan efecto inmediato.
- La pantalla de login se ve bien en 375px de ancho.

**Fuera de alcance:** auto-registro público, recuperar contraseña, OAuth, refresh tokens.
**Depende de:** nada.
**Estimación:** 2 días (la historia más cara; bloquea a todas las demás).

---

## HU-2 — Gestionar el padrón del estudio

> Como **propietario de un estudio**, quiero dar de alta, editar y dar de baja a las personas de mi estudio con su rol, para controlar quién trabaja en mis obras.

**Criterios de aceptación**

- Listado de miembros del estudio con nombre, email, rol (`owner` / `architect` / `client`) y estado.
- Alta con nombre, email y rol. Como la identidad es global, el email puede pertenecer a alguien que ya tiene cuenta por trabajar con otro estudio: en ese caso **se lo agrega al padrón** en vez de crear una cuenta nueva, y si no existe, se crea con una contraseña temporal.
- El alta responde lo mismo exista o no el email: **nunca se revela** si una persona ya tiene cuenta en la plataforma. Si ya existía, se conserva su nombre actual y la UI lo dice.
- Edición: puedo cambiar el rol de un miembro. El email no se edita — es su identidad global, no un dato de mi estudio.
- Baja del padrón: lógica. La persona deja de ver este estudio, pero sigue pudiendo loguearse y trabajar en otros. Sus asignaciones a obras de este estudio quedan inertes, **no se borran**: si la reincorporo, vuelven solas.
- No puedo darme de baja a mí mismo ni quitarme el rol de `owner`. Un estudio siempre tiene exactamente un propietario activo.
- Un miembro con rol de estudio `client` solo puede recibir el rol `client` en las obras.
- La sección exige los permisos de gestión del padrón (`member.add`, `member.edit_role`, `member.remove`; ver [ADR-002 §7](../adr/0002-authorization-model.md)): un `architect`, que solo tiene `member.view`, entra por URL directa y recibe 403; si el estudio de la URL no es suyo, recibe 404.
- El listado se ve bien en 375px de ancho.

**Fuera de alcance:** invitaciones por email, recuperación de contraseña, roles a medida, transferencia de propiedad del estudio, foto de perfil.
**Depende de:** HU-1 y T-03 (contexto de estudio).
**Estimación:** 2 días.

---

## HU-3 — Gestionar obras (ABM)

> Como **arquitecto**, quiero crear y administrar varias obras para organizar por separado la información de cada proyecto.

**Criterios de aceptación**

- Listado de obras con nombre, dirección, fecha estimada de inicio y cliente.
- Alta/edición con: nombre (obligatorio), descripción, dirección, fecha estimada de inicio, cliente.
- El cliente se elige de un desplegable alimentado por el **padrón de mi estudio filtrado por rol `client`** — nunca por la tabla global de usuarios. El campo puede quedar vacío.
- El cliente se guarda como una **asignación a la obra** con rol `client`, no como una columna de `project`. Hay a lo sumo uno por obra.
- La obra pertenece al estudio en el que estoy actuando, y al crearla **quedo asignado como `lead`** en la misma transacción: si eso no pasa, creo una obra que después no puedo ver.
- Solo veo las obras del estudio activo donde soy miembro. Si pido por URL una obra ajena —de otro miembro o de otro estudio— recibo 404 (no 403 — no revelamos que existe).
- El `owner` del estudio ve todas las obras de su estudio, porque tiene el permiso `project.view_all`. Sigue sin ver las de otros estudios.
- Baja lógica.
- Al entrar a una obra veo su pantalla de detalle, con el nombre visible como contexto en toda la navegación interna.
- El listado se ve como tarjetas en mobile, no como tabla horizontal.

**Fuera de alcance:** invitar clientes por email, adjuntar planos, estado de la obra, presupuesto.
**Depende de:** HU-1, T-03 y el padrón de HU-2 (el selector de clientes se puede enchufar al final).
**Estimación:** 2 días.

---

## HU-4 — Consultar el catálogo de materiales

> Como **arquitecto**, quiero consultar el catálogo de materiales del sistema con su unidad y precio de referencia, para saber con qué insumos y a qué costo se calculan los cómputos de mis obras.

**Criterios de aceptación**

- Listado de materiales con nombre, unidad de medida y precio de referencia.
- El catálogo es **del sistema**, igual para todos los estudios y de **solo lectura**: se carga por migración/seed, no por pantalla. Ningún endpoint escribe en él.
- Buscador por nombre en el listado.
- El precio se guarda como decimal (nunca float) y se muestra formateado en pesos. La moneda es ARS fija, con el campo modelado para el futuro.
- La sección exige el permiso `catalog.view`.
- El listado se ve bien en 375px de ancho.

**Fuera de alcance:** alta, edición y baja de materiales por pantalla; catálogo o precios propios de cada estudio; precios por proveedor; importación CSV; historial de precios; categorías/rubros; multi-moneda real.
**Depende de:** HU-0 y HU-1. Se desarrolla en paralelo con HU-2/HU-3.
**Estimación:** 0,5 día — bajó de 1,5 al dejar de ser un ABM.
**Definida por:** [ADR-003](../adr/0003-recipe-catalog.md). El catálogo pasó a ser de la plataforma para que la aplicación sirva desde el minuto cero: si fuera de cada estudio, cada uno arrancaría con una pantalla en blanco pidiendo cargar a mano las proporciones del rubro.

---

## HU-5 — Computar los materiales de una obra

> Como **arquitecto**, quiero registrar qué recetas constructivas lleva mi obra y en qué cantidad, para saber cuántos materiales necesito y cuánto me van a costar.

**Criterios de aceptación**

- Dentro del detalle de una obra hay una sección "Cómputo".
- Alta: elijo una receta del catálogo del sistema y cargo la cantidad (numérica > 0), expresada en la unidad de esa receta. Opcionalmente una nota que la ubique ("planta baja", "sector A").
- El listado muestra las líneas de esa obra y solo de esa.
- Puedo editar la cantidad de una línea y darla de baja (baja lógica).
- La obra muestra el **cómputo de materiales**: por cada material, la cantidad total que hace falta y su costo estimado, sumando todas las líneas.
- Una obra puede tener **dos líneas de la misma receta** —computar por sectores es normal— y las cantidades se suman.
- Si la obra no tiene líneas cargadas, veo un estado vacío con un llamado a la acción, no una tabla en blanco.
- Ver el cómputo exige `project.recipe.view` y modificarlo exige `project.recipe.manage`. **El costo exige `project.cost.view`, que el rol `client` no tiene**: el cliente ve cuántos materiales lleva su obra, no lo que le cuestan al estudio.
- El alta se puede completar entera desde el celular.

**Fuera de alcance:** crear o editar recetas (el catálogo es del sistema); personalizar una receta para una obra; composición de recetas dentro de recetas; mano de obra y equipo; jerarquía EDT; costos indirectos y utilidad.
**Depende de:** HU-0, HU-1, HU-3 y T-03 (el permiso de costo).
**Estimación:** 2 días — subió de 1,5 porque además del alta ahora entrega el cómputo.
**Definida por:** [ADR-003](../adr/0003-recipe-catalog.md). Las recetas pasaron de estar fuera de alcance a ser el centro de la historia: son la promesa del producto. Se descartó la composición de componentes dentro de componentes.

---

## HU-6 — Gestionar los miembros de una obra

> Como **responsable de una obra**, quiero asignar y quitar personas de mi equipo con su rol para controlar quién puede ver y editar esta obra.

**Criterios de aceptación**

- Dentro del detalle de la obra hay una sección "Equipo" con los miembros: nombre, rol en la obra y fecha de alta.
- Agrego personas eligiendo del **padrón de mi estudio**. El desplegable nunca muestra usuarios de otros estudios ni de la tabla global de usuarios.
- Roles asignables: `lead`, `collaborator`, `viewer`, `client`.
- Un miembro con rol de estudio `client` **solo** puede recibir el rol `client`: el desplegable ni siquiera le ofrece los otros.
- Hay a lo sumo un `lead` y a lo sumo un `client` por obra.
- Asignar `lead` a otra persona **transfiere** el rol en una sola transacción: el anterior queda como `collaborator`, la obra nunca se queda sin responsable ni con dos.
- Puedo cambiar el rol de un miembro que ya está, y puedo quitarlo. Quien queda fuera deja de ver la obra inmediatamente.
- No puedo quitarme a mí mismo si soy el único `lead`.
- La sección exige el permiso `project.member.manage`. Un `collaborator` ve el equipo (`project.member.view`) pero no puede modificarlo: los controles de edición directamente no aparecen, y si llama al endpoint igual recibe 403.
- El cliente que se asigna acá es **el mismo** que muestra el listado de obras de HU-3: una sola fuente, no dos lugares donde cargar lo mismo.
- La sección se usa bien desde el celular.

**Fuera de alcance:** invitaciones por email, permisos por componente, historial de cambios del equipo, notificaciones al asignado.
**Depende de:** HU-2 (padrón) y HU-3 (obras).
**Estimación:** 1 día.

---

## HU-7 — Alta de estudios y cuentas (soporte)

> Como **soporte del sistema**, quiero dar de alta un estudio junto con su propietario para incorporar nuevos estudios a la plataforma.

**Criterios de aceptación**

- Alta de estudio con nombre, email de contacto y teléfono y, **en la misma transacción**, su usuario `owner`. Un estudio sin dueño es un estudio al que nadie puede entrar: no puede existir ni por un instante.
- Si el email del propietario ya pertenece a alguien, se lo asigna como propietario sin crear una cuenta nueva.
- Listado de estudios con nombre, cantidad de miembros y estado.
- Suspender y reactivar un estudio (baja lógica). Un estudio suspendido no deja entrar a sus miembros.
- Puedo resetear la contraseña de un usuario.
- El soporte **no ve obras, componentes ni presupuestos de ningún estudio**, y no existe endpoint que se lo permita. Administra cuentas, no contenido.
- El soporte no puede asignarse a sí mismo roles de estudio ni de obra.
- Solo un usuario con rol de plataforma `support` accede a esta sección.
- Mientras esta historia no esté implementada, los estudios y sus propietarios se cargan por **seed/migración** — la plataforma funciona igual sin estas pantallas.

**Fuera de alcance:** impersonación de usuarios, facturación, métricas de uso, auto-registro público, invitaciones por email.
**Depende de:** T-02 y HU-1.
**Estimación:** 1,5 días.
**Prioridad baja:** es la primera candidata a quedar fuera del Sprint 1, porque el seed la reemplaza y no aparece en la demo.

---

## Orden de ejecución propuesto

| Días | Persona A | Persona B |
|---|---|---|
| 1 | Actualizar historias + cerrar las decisiones de modelo de `material` y `building_component` (juntos) — **hecho**, ver [ADR-003](../adr/0003-recipe-catalog.md) | idem |
| 2-3 | T-02 (esquema + seeds: permisos, roles, unidades, 2 estudios) | HU-0 + theme y layout de Mantine + **deploy andando** |
| 4-5 | HU-1 backend (auth, JWT) | HU-1 front (login, guard, selector de estudio) |
| 6 | **T-03 (motor de autorización)** — de a dos | idem |
| 7-8 | HU-2 (padrón del estudio) | HU-3 backend (obras) |
| 9-10 | HU-3 front + HU-6 (miembros de obra) | HU-5 (componentes) |
| 11-12 | HU-4 si sobra tiempo; si no, seed realista y responsive | QA cruzado, tests de aislamiento, arreglos |

Camino crítico: **T-02 → HU-1 → T-03 → HU-3 → HU-5**.

Dos avisos sobre este plan:

- **T-03 va antes del primer endpoint que lea datos de una obra.** Si va después es retrofit, y el retrofit de autorización es de donde salen los agujeros.
- Si el día 6 T-03 no está terminado, lo que se suelta es **HU-4 entera**, no el motor de autorización.

## Habilitadoras técnicas

No son historias de usuario, pero ocupan días del sprint y sin ellas no hay nada que demostrar.

- **T-02 — Esquema inicial y seeds.** Las tablas de ADR-002 más `unit_of_measure`; seeds de `permission`, `role`, `role_permission`, las 7 unidades, el usuario de soporte y **dos estudios** con su propietario. Dos estudios desde el día uno hacen que el aislamiento entre tenants sea demostrable en la defensa. *2 días.*
- **T-03 — Motor de autorización.** Resolución del estudio activo desde la URL con verificación de padrón; dependencia `requires(permission, ámbito)`; repositorio base que inyecta `firm_id` en toda lectura; tests de aislamiento parametrizados sobre la tabla de rutas de FastAPI. *1 día, de a dos.*
