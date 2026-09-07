# Historias de Usuario — Sprint 1 (MVP)

**Materia:** Proyecto Integral de Desarrollo — UCAio
**Duración del sprint:** 2 semanas
**Equipo:** 2-3 personas (fullstack)

## Decisiones de alcance confirmadas

El modelo de usuarios, roles y permisos está definido en [ADR-002](../adr/0002-authorization-model.md). Esa ADR es la fuente de verdad; si algo de este documento la contradice, gana la ADR.

- La plataforma es **multi-estudio**: varios estudios de arquitectura la usan en paralelo y ninguno ve datos de otro.
- Una persona tiene **una sola cuenta** y puede pertenecer a varios estudios, con un rol distinto en cada uno.
- Hay roles en **tres ámbitos**: `soporte` (plataforma), `propietario` / `arquitecto` / `cliente` (estudio) y `responsable` / `colaborador` / `lector` / `cliente` (obra).
- El **cliente** de una obra es un miembro del estudio con rol `cliente`, asignado a esa obra. No es una columna de `obra`.
- Los estudios los da de alta el **soporte**; no hay auto-registro público.
- Cada persona ve únicamente **las obras de las que es miembro**, dentro del estudio en el que está actuando.
- Los endpoints chequean **permisos** (`obra.editar`), nunca roles. Recurso ajeno → **404**, nunca 403.
- La moneda de los precios es **ARS fijo**, pero el campo `moneda` se modela desde ahora para soportar otras monedas más adelante.
- Todos los ABM usan **baja lógica** (`is_active`), nunca `DELETE` físico.

---

## T-01 — Definir el nombre de la aplicación

Tarea de equipo, no historia de usuario. Timebox: 30 minutos. Bloquea el repo, Figma, el deploy y la presentación — se resuelve antes que cualquier otra cosa.

**Resuelta:** el nombre es **warchitecture** (es el nombre del repo y del proyecto).

---

## HU-0 — Catálogo de unidades de medida

*Habilitadora técnica: chica, pero desbloquea HU-4 y HU-5.*

> Como **sistema**, necesito un catálogo cerrado de unidades de medida para que materiales y componentes se expresen siempre con las mismas unidades y los cómputos futuros sean calculables.

**Criterios de aceptación**

- Existe la tabla `unidad_medida` con `id`, `codigo` (m2, m3, ml, u, kg, bolsa, lt), `nombre`, `abreviatura`.
- Se carga por migración/seed, no por pantalla.
- Hay un endpoint `GET /unidades-medida` que devuelve la lista.
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
- Existen por seed un usuario `soporte` y, por cada estudio semilla, su `propietario`, para poder entrar la primera vez.
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

- Listado de miembros del estudio con nombre, email, rol (`propietario` / `arquitecto` / `cliente`) y estado.
- Alta con nombre, email y rol. Como la identidad es global, el email puede pertenecer a alguien que ya tiene cuenta por trabajar con otro estudio: en ese caso **se lo agrega al padrón** en vez de crear una cuenta nueva, y si no existe, se crea con una contraseña temporal.
- El alta responde lo mismo exista o no el email: **nunca se revela** si una persona ya tiene cuenta en la plataforma. Si ya existía, se conserva su nombre actual y la UI lo dice.
- Edición: puedo cambiar el rol de un miembro. El email no se edita — es su identidad global, no un dato de mi estudio.
- Baja del padrón: lógica. La persona deja de ver este estudio, pero sigue pudiendo loguearse y trabajar en otros. Sus asignaciones a obras de este estudio quedan inertes, **no se borran**: si la reincorporo, vuelven solas.
- No puedo darme de baja a mí mismo ni quitarme el rol de `propietario`. Un estudio siempre tiene exactamente un propietario activo.
- Un miembro con rol de estudio `cliente` solo puede recibir el rol `cliente` en las obras.
- La sección exige el permiso `miembro.gestionar`: un `arquitecto` que entra por URL directa recibe 403; si el estudio de la URL no es suyo, recibe 404.
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
- El cliente se elige de un desplegable alimentado por el **padrón de mi estudio filtrado por rol `cliente`** — nunca por la tabla global de usuarios. El campo puede quedar vacío.
- El cliente se guarda como una **asignación a la obra** con rol `cliente`, no como una columna de `obra`. Hay a lo sumo uno por obra.
- La obra pertenece al estudio en el que estoy actuando, y al crearla **quedo asignado como `responsable`** en la misma transacción: si eso no pasa, creo una obra que después no puedo ver.
- Solo veo las obras del estudio activo donde soy miembro. Si pido por URL una obra ajena —de otro miembro o de otro estudio— recibo 404 (no 403 — no revelamos que existe).
- El `propietario` del estudio ve todas las obras de su estudio, porque tiene el permiso `obra.ver_todas`. Sigue sin ver las de otros estudios.
- Baja lógica.
- Al entrar a una obra veo su pantalla de detalle, con el nombre visible como contexto en toda la navegación interna.
- El listado se ve como tarjetas en mobile, no como tabla horizontal.

**Fuera de alcance:** invitar clientes por email, adjuntar planos, estado de la obra, presupuesto.
**Depende de:** HU-1, T-03 y el padrón de HU-2 (el selector de clientes se puede enchufar al final).
**Estimación:** 2 días.

---

## HU-4 — Gestionar materiales (ABM)

> Como **arquitecto**, quiero mantener un catálogo de materiales con su unidad y precio de referencia para poder usarlos después en los cómputos de mis obras.

**Criterios de aceptación**

- Listado de materiales con nombre, unidad de medida y precio de referencia.
- Alta/edición: nombre (obligatorio, único), unidad de medida (del catálogo HU-0), precio de referencia (numérico ≥ 0, con decimales), moneda (fija en ARS por ahora, campo modelado para el futuro).
- El precio se guarda como decimal (nunca float) y se muestra formateado en pesos.
- Buscador por nombre en el listado.
- Baja lógica.
- El catálogo es **de mi estudio**, no por obra y no compartido entre estudios: los precios son información sensible de cada estudio.

**Fuera de alcance:** precios por proveedor, importación CSV, historial de precios, categorías/rubros, multi-moneda real.
**Depende de:** HU-0 y HU-1. Se desarrolla en paralelo con HU-2/HU-3.
**Estimación:** 1,5 días.
**Bloqueada:** falta decidir el modelo de `material` bajo multi-tenant (catálogo por estudio, semilla global copiada, o catálogo global con precios por estudio). Ver [modelo-datos §5](../modelo-datos-sprint-1.md). Decisión chica, pero hay que tomarla antes de empezar.

---

## HU-5 — Registrar componentes constructivos en una obra

> Como **arquitecto**, quiero registrar los componentes constructivos de una obra con su medida y unidad para tener listado y cuantificado todo lo que hay que construir.

**Criterios de aceptación**

- Dentro del detalle de una obra hay una sección "Componentes".
- Alta/edición: descripción (obligatoria), medida (numérica > 0), unidad de medida (catálogo HU-0).
- El listado muestra los componentes de esa obra y solo de esa.
- Puedo editar y dar de baja un componente.
- Si la obra no tiene componentes, veo un estado vacío con un llamado a la acción, no una tabla en blanco.
- El alta se puede completar entera desde el celular.

**Fuera de alcance:** recetas constructivas, cálculo de materiales, jerarquía EDT, costos.
**Depende de:** HU-0 y HU-3.
**Estimación:** 1,5 días.
**Bloqueada:** hay **dos modelos de componente en discusión** —componente propio de cada obra con jerarquía (`parent_id`), o plantilla global reutilizable con receta de materiales y cantidad usada por obra—. No son variantes: son definiciones distintas de qué es un componente. Ver [modelo-datos §5](../modelo-datos-sprint-1.md). **Es la decisión más urgente del sprint**: bloquea la historia que está al final del camino crítico, así que tomarla el día 1, no el día 8.

---

## HU-6 — Gestionar los miembros de una obra

> Como **responsable de una obra**, quiero asignar y quitar personas de mi equipo con su rol para controlar quién puede ver y editar esta obra.

**Criterios de aceptación**

- Dentro del detalle de la obra hay una sección "Equipo" con los miembros: nombre, rol en la obra y fecha de alta.
- Agrego personas eligiendo del **padrón de mi estudio**. El desplegable nunca muestra usuarios de otros estudios ni de la tabla global de usuarios.
- Roles asignables: `responsable`, `colaborador`, `lector`, `cliente`.
- Un miembro con rol de estudio `cliente` **solo** puede recibir el rol `cliente`: el desplegable ni siquiera le ofrece los otros.
- Hay a lo sumo un `responsable` y a lo sumo un `cliente` por obra.
- Asignar `responsable` a otra persona **transfiere** el rol en una sola transacción: el anterior queda como `colaborador`, la obra nunca se queda sin responsable ni con dos.
- Puedo cambiar el rol de un miembro que ya está, y puedo quitarlo. Quien queda fuera deja de ver la obra inmediatamente.
- No puedo quitarme a mí mismo si soy el único `responsable`.
- La sección exige el permiso `obra.miembro.gestionar`. Un `colaborador` ve el equipo (`obra.miembro.ver`) pero no puede modificarlo: los controles de edición directamente no aparecen, y si llama al endpoint igual recibe 403.
- El cliente que se asigna acá es **el mismo** que muestra el listado de obras de HU-3: una sola fuente, no dos lugares donde cargar lo mismo.
- La sección se usa bien desde el celular.

**Fuera de alcance:** invitaciones por email, permisos por componente, historial de cambios del equipo, notificaciones al asignado.
**Depende de:** HU-2 (padrón) y HU-3 (obras).
**Estimación:** 1 día.

---

## HU-7 — Alta de estudios y cuentas (soporte)

> Como **soporte del sistema**, quiero dar de alta un estudio junto con su propietario para incorporar nuevos estudios a la plataforma.

**Criterios de aceptación**

- Alta de estudio con nombre, email de contacto y teléfono y, **en la misma transacción**, su usuario `propietario`. Un estudio sin dueño es un estudio al que nadie puede entrar: no puede existir ni por un instante.
- Si el email del propietario ya pertenece a alguien, se lo asigna como propietario sin crear una cuenta nueva.
- Listado de estudios con nombre, cantidad de miembros y estado.
- Suspender y reactivar un estudio (baja lógica). Un estudio suspendido no deja entrar a sus miembros.
- Puedo resetear la contraseña de un usuario.
- El soporte **no ve obras, componentes ni presupuestos de ningún estudio**, y no existe endpoint que se lo permita. Administra cuentas, no contenido.
- El soporte no puede asignarse a sí mismo roles de estudio ni de obra.
- Solo un usuario con rol de plataforma `soporte` accede a esta sección.
- Mientras esta historia no esté implementada, los estudios y sus propietarios se cargan por **seed/migración** — la plataforma funciona igual sin estas pantallas.

**Fuera de alcance:** impersonación de usuarios, facturación, métricas de uso, auto-registro público, invitaciones por email.
**Depende de:** T-02 y HU-1.
**Estimación:** 1,5 días.
**Prioridad baja:** es la primera candidata a quedar fuera del Sprint 1, porque el seed la reemplaza y no aparece en la demo.

---

## Orden de ejecución propuesto

| Días | Persona A | Persona B |
|---|---|---|
| 1 | Actualizar historias + cerrar las decisiones de modelo de `material` y `componente` (juntos) | idem |
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

- **T-02 — Esquema inicial y seeds.** Las tablas de ADR-002 más `unidad_medida`; seeds de `permiso`, `rol`, `rol_permiso`, las 7 unidades, el usuario de soporte y **dos estudios** con su propietario. Dos estudios desde el día uno hacen que el aislamiento entre tenants sea demostrable en la defensa. *2 días.*
- **T-03 — Motor de autorización.** Resolución del estudio activo desde la URL con verificación de padrón; dependencia `requiere(permiso, ámbito)`; repositorio base que inyecta `estudio_id` en toda lectura; tests de aislamiento parametrizados sobre la tabla de rutas de FastAPI. *1 día, de a dos.*
