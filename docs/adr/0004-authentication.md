# ADR-004: Autenticación — JWT stateless en el cliente

**Estado:** Propuesta
**Fecha:** 2026-09-07
**Contexto:** HU-1 (iniciar sesión). Define cómo se prueba la identidad en cada request; toda historia posterior se apoya en esto.

## Contexto

[ADR-002](0002-authorization-model.md) cerró la **autorización**: quién puede hacer qué, y dónde. Dejó abierta la **autenticación**: cómo el backend sabe, en el request número dos, que sigue siendo la misma persona que se logueó en el request número uno.

De ADR-002 §9 viene una sola restricción, y es dura:

> Los permisos **NO** viajan en el JWT. El token dice *quién sos*; los permisos se resuelven contra la base en cada request.

Eso fija el *contenido* del token pero no su formato, ni cuánto vive, ni dónde lo guarda el navegador. Y esas tres cosas hay que decidirlas antes de escribir la primera línea de HU-1, porque cambiar de mecanismo después toca el login, el interceptor del front, el guard de rutas y la configuración de CORS a la vez.

Las restricciones del proyecto que pesan en la decisión:

- **HU-1 dice literalmente "el sistema me devuelve un token"**, y pone fuera de alcance el auto-registro, la recuperación de contraseña, OAuth y los refresh tokens.
- **Front y backend viven en dominios distintos**: Vercel el front, Render/Railway el backend ([ADR-001](0001-stack.md)). No es una app servida desde el mismo origen.
- **El sprint son 2 semanas y HU-1 está estimada en 2 días**, siendo la historia que bloquea a todas las demás.
- **No hay datos reales de clientes.** Son dos estudios semilla con contraseña conocida, para una defensa de materia.

## Decisión

### Formato: JWT firmado con HS256

El backend emite un JSON Web Token firmado con `JWT_SECRET` (HS256, ya configurado en `.env.example` y en `app/core/config.py`). Los claims son **exactamente tres**:

```json
{ "sub": "42", "iat": 1757260800, "exp": 1757264400 }
```

`sub` es el `account.id`, escrito **como string** y no como número: el RFC 7519 lo define como `StringOrURI`, y PyJWT valida ese tipo. Se convierte a `int` al decodificar. **Nada más entra ahí**: ni el email, ni el nombre, ni los roles, ni los permisos, ni el estudio activo.

- Los permisos quedan afuera por ADR-002 §9: un token con permisos adentro es un permiso congelado, y HU-2 promete que dar de baja a alguien tiene efecto inmediato.
- El **estudio activo** queda afuera por ADR-002 §9 también: va explícito en la URL (`/firms/{id}/projects`), no en la sesión ni en el token. Meterlo en el token lo volvería estado oculto que se desincroniza entre pestañas.
- El email y el nombre quedan afuera porque son datos que cambian y el token no se puede editar: se leen de la base, que es donde son ciertos.

HS256 y no RS256 porque hay un solo servicio firmando y verificando. RS256 sirve cuando el que verifica no debe poder firmar (varios servicios, o verificación en el cliente), y acá no es el caso; una clave asimétrica sería una segunda cosa que gestionar sin nada a cambio.

### Vida útil: 60 minutos, sin refresh token

`ACCESS_TOKEN_EXPIRE_MINUTES=60`. Al expirar, el backend responde `401` y el frontend manda al login. No hay refresh token — la propia HU-1 lo pone fuera de alcance.

La consecuencia hay que decirla sin maquillaje: **a la hora de trabajar, al usuario se lo desloguea y pierde lo que estuviera escribiendo en un formulario.** Se acepta porque en el uso que la historia describe (entrar, mirar obras, cargar un cómputo) y en una demo de defensa, una hora alcanza; y porque un refresh token bien hecho es rotación, detección de reuso y almacenamiento aparte — más trabajo que el resto de HU-1 junta.

### Almacenamiento en el cliente: `localStorage`

El token viaja en el body de `POST /auth/login`, el frontend lo guarda en `localStorage` bajo una única clave y lo manda en el header `Authorization: Bearer <token>`.

Esto **asume un riesgo concreto y conocido**: `localStorage` es accesible desde JavaScript, así que un XSS en el frontend permite robar el token y usarlo hasta que expire. Una cookie `httpOnly` no sería robable así.

Se acepta por tres razones, en orden de peso:

1. **La alternativa no es gratis en esta topología.** Con el front en Vercel y el backend en Render, la cookie es *cross-site*: exige `SameSite=None; Secure`, CORS con `credentials`, un token anti-CSRF propio, y convivir con navegadores que restringen cada vez más las cookies de terceros. Son cuatro piezas nuevas en la historia que bloquea a todas las demás.
2. **XSS ya es catastrófico igual.** Con una cookie `httpOnly` el atacante no se lleva el token, pero sigue pudiendo emitir requests autenticados desde la página de la víctima. La cookie limita el daño, no lo evita.
3. **No hay datos reales que proteger todavía.** Son cuentas semilla con contraseña conocida y publicada en el README del seed.

La mitigación real del XSS es la que el stack ya da: React escapa por defecto, no usamos `dangerouslySetInnerHTML`, y no hay entrada de usuario que se renderice como HTML.

### Cerrar sesión es del lado del cliente

`Cerrar sesión` borra el token del `localStorage` y redirige al login. **No hay endpoint de logout ni lista de revocación**: el token sigue siendo criptográficamente válido hasta su `exp`. Es la contracara de ser stateless — el servidor no guarda nada que pueda invalidar.

### Respuestas de error

- Credenciales inválidas → `401` con **el mismo cuerpo** para email inexistente, contraseña incorrecta y cuenta desactivada: `{"detail": "Email o contraseña incorrectos"}`. Distinguirlos convertiría el login en un enumerador de emails, que es lo que HU-1 pide evitar.
- Esa indistinción incluye el **tiempo de respuesta**: cuando el email no existe se verifica igual la contraseña contra un hash dummy, para que las dos ramas tarden lo mismo. Sin eso la diferencia no es un canal lateral sutil, es un oráculo medible con `curl`: ~2 ms para un `SELECT` indexado que no encuentra nada, contra los ~250 ms que bcrypt tarda a propósito. Dos órdenes de magnitud alcanzan para enumerar la base de usuarios sin herramientas.
- La contra, que conviene decir en vez de esconder: eso hace que **cualquiera pueda gastar 250 ms de CPU por request** con un email inventado, o sea un amplificador de denegación de servicio chiquito. La respuesta correcta a eso es rate limiting, que está fuera del alcance de HU-1 y queda anotado abajo como hueco conocido.
- Token ausente, inválido, expirado, o cuenta desactivada → `401` con `WWW-Authenticate: Bearer`.
- Estudio de la URL que no es tuyo, o inexistente, o suspendido → **`404`**, nunca 403 (ADR-002 §9).

### Identidad, en cada request

Implementa ADR-002 §9 pasos 1 y 2:

1. Se decodifica el token y se obtiene el `account_id`.
2. **Se carga la cuenta de la base** y se verifica `account.is_active`. No se confía en el token para nada más que el id.
3. Si la ruta lleva `{firm_id}`, se busca la fila de `firm_member` y se verifican **tres** banderas: `account.is_active`, `firm_member.is_active` y `firm.is_active`. Esta última no la nombra ADR-002 §9, pero HU-7 dice que un estudio suspendido no deja entrar a sus miembros.

El paso 2 es una consulta por request contra una tabla indexada, y es el precio de que revocar un acceso tenga efecto inmediato.

## Consecuencias

**Se desbloquea:**

- HU-1 completa, y con ella toda historia que necesite saber quién está del otro lado.
- El backend queda sin estado de sesión: escala horizontalmente y se reinicia sin desloguear a nadie.
- T-03 se apoya sobre `get_current_account` sin rediseñar nada: le agrega la resolución de permisos.

**Compromisos que asumimos:**

- El token es robable por XSS mientras viva. La defensa es no tener XSS.
- No se puede revocar una sesión antes de su expiración. Cambiar la contraseña de alguien **no** cierra sus sesiones abiertas.
- Al usuario se lo desloguea cada 60 minutos.
- `JWT_SECRET` es un secreto de producción de verdad: quien lo tenga puede firmar un token de cualquier cuenta. Nunca se commitea, y en el deploy se setea como variable de entorno.
- Ese secreto tiene un **largo mínimo de 32 bytes**. Con HS256 la clave es el único material secreto que hay: si es corta, un solo token capturado alcanza para adivinarla offline por fuerza bruta y a partir de ahí firmar la sesión de cualquiera. RFC 7518 §3.2 lo exige y PyJWT avisa por consola en cada llamada cuando no se cumple. Los placeholders de `.env.example` y del workflow de CI cumplen el largo para que copiar y pegar no arranque mal; el de cada ambiente se genera con `openssl rand -hex 32`.
- Rotar `JWT_SECRET` invalida todas las sesiones activas de golpe.

**Queda pendiente de revisar, y bajo qué condición:**

| Tema | Se revisa cuando |
|---|---|
| Refresh tokens | La expiración a los 60 minutos moleste en uso real, o entren sesiones largas |
| Cookie `httpOnly` + CSRF | Entren datos reales de clientes, o el front y el backend queden en el mismo dominio (que es lo que abarata la cookie) |
| Revocación del lado servidor | Se implemente el reseteo de contraseña de HU-7: resetear debería cerrar las sesiones abiertas |
| Rotación de `JWT_SECRET` | Haya sospecha de filtración, o exista un procedimiento de operación |
| Bloqueo por intentos fallidos / rate limiting | La aplicación quede expuesta a internet con datos reales |
| Segundo factor | Lo pida el cliente |

## Alternativas descartadas

**Sesión en base con cookie de sesión.** El servidor guarda la sesión y puede cerrarla cuando quiera — resuelve la revocación, que es la debilidad real del JWT. Descartada por el mismo problema cross-site que la cookie `httpOnly` (Vercel + Render) más una tabla y su limpieza periódica, para una historia que dura 2 días. Es la alternativa más defendible de esta lista.

**JWT en cookie `httpOnly` + token anti-CSRF.** Quita el token del alcance de JavaScript. Descartada por el costo de las cookies cross-site descrito arriba, y porque no evita que un XSS emita requests autenticados igual. Se reevalúa si entran datos reales.

**Refresh token de corta vida + access token de 5 minutos.** Es el diseño correcto para producción: acorta la ventana de un token robado sin deslogear al usuario. Descartada porque HU-1 lo pone explícitamente fuera de alcance, y porque hecho a medias (sin rotación ni detección de reuso) agrega superficie sin agregar seguridad.

**Roles dentro del token para que el front pinte el menú.** ADR-002 lo permite explícitamente ("el token puede llevar los roles solo para que el front decida qué menú pintar"). Descartada igual: `GET /auth/me` ya devuelve los estudios con su rol, y tener el mismo dato en dos lugares con vidas útiles distintas —el token congelado una hora, la respuesta fresca— es una contradicción esperando a pasar. Con una sola fuente, un cambio de rol se ve al recargar.

**El estudio activo dentro del token.** URLs más cortas y una query menos. Descartada por ADR-002 §9: sería estado oculto, se desincroniza entre pestañas, y el modo de falla es escribir en el estudio equivocado.

**`OAuth2PasswordRequestForm` de FastAPI para el login.** Da gratis el botón "Authorize" de `/docs`. Descartada porque obliga a mandar `form-urlencoded` y a llamar `username` a un campo que es un email, ensuciando el front y el modelo de dominio a cambio de una comodidad de la documentación. El candado de `/docs` se consigue igual con `HTTPBearer`.

**RS256 con par de claves.** Necesario cuando quien verifica no debe poder firmar. Acá firma y verifica el mismo proceso, así que sería una clave más para gestionar sin nada a cambio.

**`sessionStorage` en vez de `localStorage`.** Se limpia al cerrar la pestaña, lo que reduce un poco la exposición. Descartada porque rompe el criterio de aceptación "la sesión persiste al recargar la página" en cuanto el usuario abre la app en una pestaña nueva, y frente a XSS es exactamente igual de vulnerable.

## Fuera de alcance de esta ADR

Auto-registro público, recuperación de contraseña, invitaciones por email, OAuth con proveedores externos, segundo factor, impersonación de soporte y auditoría de inicios de sesión. La resolución de **permisos** —qué puede hacer la persona una vez identificada— es de [ADR-002](0002-authorization-model.md) y se implementa en T-03.

## Referencias

- RFC 7519 (JSON Web Token) y RFC 8725 (*JWT Best Current Practices*).
- OWASP *Cheat Sheet Series*: **Authentication**, **Session Management**, **JSON Web Token for Java** (la sección de almacenamiento en cliente aplica a cualquier stack).
- OWASP Top 10 (2021) A07 *Identification and Authentication Failures*.
- OWASP *Authentication Cheat Sheet*, §"Authentication Responses" — de ahí viene la respuesta genérica y el tiempo constante.

> Las referencias se citaron de memoria durante el diseño: verificar números de RFC y secciones antes de usarlas en la defensa.
