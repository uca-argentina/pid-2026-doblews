# Historias de Usuario — Sprint 1 (MVP)

**Materia:** Proyecto Integral de Desarrollo — UCAio
**Duración del sprint:** 2 semanas
**Equipo:** 2-3 personas (fullstack)

## Decisiones de alcance confirmadas

- El **cliente** de una obra es un usuario del sistema con rol `cliente` (no texto libre).
- Existe un rol `admin` que da de alta usuarios; no hay auto-registro público.
- Cada **arquitecto ve únicamente las obras de las que es miembro** (filtrado por usuario desde el Sprint 1).
- La moneda de los precios es **ARS fijo**, pero el campo `moneda` se modela desde ahora para soportar otras monedas más adelante.
- Todos los ABM usan **baja lógica** (`is_active`), nunca `DELETE` físico.

---

## T-01 — Definir el nombre de la aplicación

Tarea de equipo, no historia de usuario. Timebox: 30 minutos. Bloquea el repo, Figma, el deploy y la presentación — se resuelve antes que cualquier otra cosa.

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
- Existe al menos un usuario administrador cargado por seed para poder entrar la primera vez.
- La pantalla de login se ve bien en 375px de ancho.

**Fuera de alcance:** auto-registro público, recuperar contraseña, OAuth, refresh tokens.
**Depende de:** nada.
**Estimación:** 2 días (la historia más cara; bloquea a todas las demás).

---

## HU-2 — Gestionar usuarios (ABM)

> Como **administrador**, quiero dar de alta, editar y desactivar usuarios con su rol para controlar quién accede a la plataforma.

**Criterios de aceptación**

- Listado de usuarios con nombre, email, rol y estado (activo/inactivo).
- Alta: nombre, email, contraseña, rol (`admin` / `arquitecto` / `cliente`).
- El email es único; si se repite, error claro en el formulario.
- Edición: puedo cambiar nombre y rol; el email no se edita (o se edita validando unicidad — a definir en implementación).
- Baja lógica: el usuario queda inactivo y no puede loguearse, pero no se borra (las obras siguen referenciándolo).
- Solo el rol `admin` ve esta sección; un `arquitecto` que entra por URL directa recibe 403.
- No puedo desactivarme a mí mismo.

**Fuera de alcance:** invitaciones por email, permisos granulares, foto de perfil.
**Depende de:** HU-1.
**Estimación:** 1,5 días.

---

## HU-3 — Gestionar obras (ABM)

> Como **arquitecto**, quiero crear y administrar varias obras para organizar por separado la información de cada proyecto.

**Criterios de aceptación**

- Listado de obras con nombre, dirección, fecha estimada de inicio y cliente.
- Alta/edición con: nombre (obligatorio), descripción, dirección, fecha estimada de inicio, cliente.
- El cliente se elige de un desplegable de usuarios con rol `cliente`; el campo puede quedar vacío.
- Solo veo las obras donde soy miembro (arquitecto asignado). Si pido por URL una obra ajena, recibo 404 (no 403 — no revelamos que existe).
- Baja lógica.
- Al entrar a una obra veo su pantalla de detalle, con el nombre visible como contexto en toda la navegación interna.
- El listado se ve como tarjetas en mobile, no como tabla horizontal.

**Fuera de alcance:** invitar clientes por email, adjuntar planos, estado de la obra, presupuesto.
**Depende de:** HU-1 (y del selector de clientes de HU-2, que se puede enchufar al final).
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
- El catálogo es global, no por obra.

**Fuera de alcance:** precios por proveedor, importación CSV, historial de precios, categorías/rubros, multi-moneda real.
**Depende de:** HU-0 y HU-1. Se desarrolla en paralelo con HU-2/HU-3.
**Estimación:** 1,5 días.

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
**Nota de modelado:** aunque la jerarquía no entra en este sprint, la tabla lleva `parent_id` nullable desde la primera migración, para no necesitar una migración fea cuando se implemente la EDT.

---

## Orden de ejecución propuesto

| Días | Persona A | Persona B |
|---|---|---|
| 1 | T-01 + historias + setup del repo (juntos) | idem |
| 2 | HU-1 backend (auth, seed, JWT) | HU-0 + scaffold front + deploy |
| 3-4 | HU-1 front (login, guard, layout) | HU-4 (materiales, full stack) |
| 5-6 | HU-2 (usuarios) | HU-3 backend (obras) |
| 7-8 | HU-3 front + selector de cliente | HU-5 (componentes) |
| 9-10 | Responsive + seed realista | QA cruzado + arreglos |
| 11-12 | Demo, presentación, buffer | idem |

Camino crítico: **HU-1 → HU-3 → HU-5**. HU-4 no depende de ese camino, por eso arranca temprano y en paralelo.
