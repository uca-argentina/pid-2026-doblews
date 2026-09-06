# Glosario — Stack de frontend

Qué es y para qué sirve cada pieza del frontend definido en [ADR-001](adr/0001-stack.md). Pensado para
alguien que arranca en el proyecto y no conoce todavía estas herramientas — no reemplaza al ADR (que
explica *por qué* se eligió cada una), solo explica *qué son*. Complementa a
[glosario-stack-backend.md](glosario-stack-backend.md).

---

## Capa de UI: qué renderiza la pantalla

**React** — una librería para construir interfaces mediante componentes: funciones que reciben datos
(`props`) y devuelven qué hay que mostrar en pantalla. Cuando el estado cambia, React recalcula qué
cambió realmente en el DOM y actualiza solo eso, en vez de redibujar toda la página. Es la base de todo
lo demás en el frontend — Mantine son componentes de React, React Router decide qué componente mostrar
según la URL, etc.

**TypeScript** — JavaScript con tipos. Le agrega a JS la posibilidad de decir "esta función recibe un
`string` y devuelve un `number`", y el compilador (`tsc`) avisa en el editor si hay un error, antes de
correr una sola línea. No es un lenguaje aparte: todo TypeScript se convierte en JavaScript normal al
compilar, porque el navegador no entiende TypeScript.

**SPA (Single Page Application)** — el patrón que sigue este proyecto: el navegador carga una sola vez
el HTML/JS/CSS, y a partir de ahí todo lo que se ve (cambiar de "Obras" a "Materiales") pasa
reescribiendo el DOM con JavaScript, sin pedirle una página nueva al servidor. Por eso el backend es
"solo" una API (devuelve JSON) y no HTML — la interfaz la arma React en el navegador. Es lo opuesto a un
sitio con Server-Side Rendering (SSR) como Next.js, que el ADR-001 descartó a propósito.

## Capa de build: cómo el código llega al navegador

**Vite** — un bundler: toma todos los archivos `.tsx`/`.ts`/`.css` (que el navegador no puede
interpretar directamente tal como se escriben, con imports de módulos, JSX, etc.) y los empaqueta en
archivos finales que sí entiende. En desarrollo, además, sirve el código con hot reload: al guardar un
cambio, actualiza la página en el navegador al instante, sin recargarla entera ni perder el estado (por
ejemplo, lo que estaba tipeado en un formulario). Es el reemplazo moderno de herramientas más viejas y
lentas como Webpack.

**JSX/TSX** — la sintaxis que mezcla HTML dentro de JavaScript/TypeScript (`<div>{nombre}</div>` dentro
de una función). No es HTML real ni JS válido por sí solo — Vite lo transforma (vía
`@vitejs/plugin-react`) en llamadas normales de JavaScript que React entiende.

## Capa de componentes y estilos

**Mantine** — la librería de componentes de UI elegida en el ADR-001: botones, tablas, modales,
selectores de fecha, formularios, ya hechos y con un diseño consistente, para no reinventar cada input
desde cero. Se divide en paquetes (`core`, `form`, `dates`, `notifications`, `charts`) que se instalan
por separado según lo que se necesite. Necesita el `MantineProvider` envolviendo la app para que todos
los componentes compartan el mismo tema (colores, tamaños, breakpoints).

**PostCSS** — un procesador de CSS: toma el CSS y lo transforma antes de que llegue al navegador,
aplicando plugins. Es como Babel pero para hojas de estilo. En este proyecto se usa para que funcionen
las variables y los breakpoints responsive que necesita Mantine (`postcss-preset-mantine`,
`postcss-simple-vars`).

## Capa de datos: cómo se habla con el backend

**Axios** — un cliente HTTP: la librería que arma y envía el request (`GET`, `POST`, etc.) al backend y
devuelve la respuesta. Es el equivalente frontend de lo que `httpx` es en los tests del backend, o
`psycopg` para la base de datos — la pieza que efectivamente abre la conexión de red.

**TanStack Query (React Query)** — maneja el estado del servidor dentro de React: cuando se piden datos
con `useQuery`, cachea la respuesta, evita pedir lo mismo dos veces si dos componentes lo necesitan,
reintenta automáticamente si falla, y refresca los datos solo cuando corresponde. Sin esto, cada
componente tendría que manejar a mano loading/error/cache con `useState` y `useEffect` — se vuelve
repetitivo y propenso a bugs (pedir datos de más, mostrar datos viejos).

**React Router (react-router-dom)** — decide qué componente mostrar según la URL actual, todo en el
navegador (sin pedirle nada al servidor). Es lo que hace posible que `/obras` muestre el listado y
`/obras/12` el detalle de una obra puntual, dentro de una SPA.

**dayjs** — una librería chica para trabajar con fechas (sumar días, formatear, comparar). La necesita
`@mantine/dates` para sus selectores de fecha; es una alternativa liviana a librerías más pesadas como
Moment.js.

## Capa de calidad

**ESLint** — el linter de JavaScript/TypeScript: detecta código sospechoso (variables sin usar, hooks
de React mal usados, imports rotos) antes de que sea un bug en producción. Es el equivalente de `ruff`
en el backend.

**Prettier** — el formatter: reescribe el código con un estilo fijo (comillas, indentación, punto y
coma) para que nadie discuta estilo en un PR. Equivalente de `black` en el backend.

## La herramienta que orquesta todo esto

**npm** — el gestor de paquetes de Node.js: instala las dependencias declaradas en `package.json`, y
guarda las versiones exactas resueltas en `package-lock.json` (para que todo el equipo instale lo
mismo). Es el equivalente de `uv` en el backend, aunque más limitado — no gestiona la versión de Node en
sí, solo los paquetes.
