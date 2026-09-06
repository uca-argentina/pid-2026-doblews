# Glosario — Stack de backend

Qué es y para qué sirve cada pieza del backend definido en [ADR-001](adr/0001-stack.md). Pensado para
alguien que arranca en el proyecto y no conoce todavía estas herramientas — no reemplaza al ADR (que
explica *por qué* se eligió cada una), solo explica *qué son*.

---

## Capa web: qué sirve las requests HTTP

**FastAPI** — un framework de Python para construir APIs web. Un framework da la estructura (cómo se
define una ruta, cómo se lee el body de un request, cómo se devuelve una respuesta) para escribir solo
la lógica de negocio. Es async (puede atender otra request mientras espera una consulta a la base, en
vez de quedarse bloqueado) y genera documentación interactiva sola (Swagger, en `/docs`) a partir del
código — no se escribe aparte, se deduce de los tipos que se usan.

**Uvicorn** — un servidor ASGI. FastAPI define *qué* responder, pero no sabe escuchar un puerto de red
ni hablar el protocolo HTTP a bajo nivel — eso lo hace un servidor. Uvicorn recibe la conexión y se la
pasa a la app de FastAPI. Se usa en desarrollo con `uv run uvicorn app.main:app --reload` (`--reload`
reinicia solo cuando cambia un archivo).

**Gunicorn** — otro servidor, pensado para producción: en vez de atender todo con un solo proceso,
levanta varios *workers* para aprovechar varios núcleos de CPU y sobrevivir si uno se cuelga. En
producción se usa como manager de procesos, con Uvicorn como motor async adentro de cada worker
(`gunicorn -k uvicorn.workers.UvicornWorker`) — no son competidores, se combinan.

## Capa de datos: cómo se habla con Postgres

**SQLAlchemy** — un ORM (Object-Relational Mapper): permite representar tablas de la base como clases
de Python (`class Usuario(Base): ...`) y filas como objetos (`usuario.email`), en vez de escribir SQL a
mano todo el tiempo. La versión 2.0 (la que usa el proyecto) soporta tipado — `Mapped[str]` le dice
tanto a Python como a SQLAlchemy qué tipo tiene esa columna.

**psycopg** — el driver: la librería que efectivamente abre una conexión TCP con Postgres y habla su
protocolo binario. SQLAlchemy no se conecta a una base por sí solo, delega en un driver específico de
cada motor. Se usa casi siempre por debajo de SQLAlchemy, rara vez directo.

**Alembic** — la herramienta de migraciones: versiona los cambios al esquema de la base (crear una
tabla, agregar una columna) como archivos Python numerados y ordenados, cada uno con un `upgrade()` y
un `downgrade()`. Sin esto, cambiar el esquema significa correr SQL a mano en cada máquina (la de cada
uno, producción) y arriesgarse a que se desincronicen. Con Alembic, `alembic upgrade head` deja
cualquier base al día corriendo la misma secuencia de cambios. Por eso el ADR-001 lo marca "no
negociable desde la primera migración".

## Capa de validación y configuración

**Pydantic** — valida y serializa datos usando type hints de Python. Si se define
`class LoginRequest(BaseModel): email: str; password: str`, Pydantic garantiza que el JSON que llega
tiene esos dos campos con esos tipos, o rechaza el request con un error claro, sin escribir un solo
`if`. FastAPI lo usa por dentro: los tipos que se ponen en la firma de un endpoint son en realidad
modelos Pydantic.

**pydantic-settings** — una extensión de Pydantic pensada para configuración: define una clase
`Settings` con los campos esperados (`DATABASE_URL`, `JWT_SECRET`, etc.) y los lee automáticamente de
variables de entorno o de un `.env`, con el mismo tipado y validación que Pydantic. Es el "config por
variables de entorno, no hardcodeado" que pide la ADR-001. Todavía no está escrito en el repo
(`app/core/config.py` sigue vacío).

## Capa de autenticación (para HU-1, todavía sin código)

**PyJWT** — genera y valida JWT (JSON Web Tokens): un token firmado que codifica quién es el usuario
(y qué roles tiene) sin que el servidor tenga que guardar sesión en memoria. Al loguearse, el backend
entrega un JWT; en cada request siguiente se manda ese token y el backend lo valida y confía en lo que
dice adentro, sin ir a la base de nuevo.

**passlib[bcrypt]** — hashea contraseñas. Nunca se guarda la contraseña tal cual en la base (si alguien
roba la base, tendría todas las contraseñas en texto plano); se guarda un hash — una transformación de
un solo sentido, no reversible. `bcrypt` es el algoritmo específico, diseñado para ser lento a propósito
(dificulta probar contraseñas por fuerza bruta).

**python-multipart** — le permite a FastAPI leer datos de formularios HTML normales
(`multipart/form-data`), distinto de JSON. Es requisito técnico de FastAPI para ciertos flujos de auth
con formularios.

## Capa de testing y calidad

**pytest** — el framework de tests de Python: se escriben funciones `def test_algo(): assert ...` y
las descubre y corre solas, con buen reporte de qué falló y por qué.

**pytest-asyncio** — extensión de pytest para poder testear funciones `async` (como los endpoints de
FastAPI), que pytest no maneja de forma nativa.

**httpx** — un cliente HTTP (como `requests`, pero con soporte async). Se usa en los tests para simular
un request real contra la app de FastAPI sin necesidad de levantar un servidor de verdad.

**ruff** — un linter (detecta código sospechoso o mal escrito: imports sin usar, variables no
definidas, estilo) y también formatter (reordena imports). Es muy rápido porque está escrito en Rust, y
reemplaza a varias herramientas viejas de Python (flake8, isort, etc.) en una sola.

**black** — un formatter de código: reescribe el código con un estilo fijo (indentación, comillas,
saltos de línea) para que nadie discuta estilo en un PR — "así lo formatea black" y listo.

## La herramienta que orquesta todo esto

**uv** — el gestor de proyecto Python que se usa en vez de `pip`/`venv` manuales. Hace tres cosas: (1)
descarga e instala la versión de Python que se pida, aunque no esté en el sistema, (2) resuelve y guarda
las versiones exactas de cada dependencia en `uv.lock` (así todo el equipo instala exactamente lo
mismo), y (3) crea y gestiona el entorno virtual (`.venv/`) automáticamente. `uv add fastapi` agrega una
dependencia; `uv run <comando>` corre algo dentro de ese entorno sin activarlo a mano.
