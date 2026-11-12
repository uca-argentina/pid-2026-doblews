# Guía de trabajo: "si tocás esto, fijate también en aquello"

Esta guía no te da plantillas largas de código: te dice **qué cambia en cadena**, en **qué archivo** y en **qué función existente** hay que agregar algo. Casi todos los errores que tuvimos en las prácticas fueron de este tipo: se cambió una cosa y se olvidó otra que dependía de ella. Donde la ubicación exacta importa, hay una línea corta entre comillas.

**Cómo se lee "además, en la función X":** significa que no alcanza con crear algo nuevo; hay que **abrir una función que ya existe** y agregarle una línea. Son los olvidos que no dan error de sintaxis, pero hacen fallar la feature.

**Cómo usarla:** trabajá un archivo por vez, en el orden de abajo. Al terminar cada archivo, mirá la sección "Qué cambia en cadena" de ese archivo, y después corré el chequeo rápido (al final). Nunca avances con algo en rojo.

Orden general, de abajo hacia arriba:
base de datos → schemas → repositorio → servicio → ruta → probar en /docs → service del front → hook → componentes → página → probar en el navegador.

---

## Paso 0. Leer la consigna (antes de abrir ningún archivo)

1. Marcá cada frase y preguntate qué capa toca (ver tabla).
2. Buscá una feature parecida que ya exista y seguí sus huellas con `grep` sobre backend y frontend. Los archivos que aparecen son tu lista, pero **no todo lo que aparece corresponde**: clasificalo con la consigna.
3. Anotá la lista de archivos en orden y andá tachando.

| Si la consigna dice... | Entonces toco |
|---|---|
| "un dato nuevo" en algo existente | modelo, migración, schema de salida, mapeo de la ruta, tipo del front, y donde se muestre |
| "el usuario lo carga o edita" | además: schemas Create/Update, servicio (alta/edición), formulario del front |
| "se cambia con una acción propia" (marcar, archivar, aprobar) | NO va en Create/Update: va solo en el schema de salida + endpoint nuevo |
| "un endpoint nuevo" | ruta y servicio; repo solo si necesitás una consulta que no existe |
| "un filtro opcional" | ruta, repo y, en el front, service + hook + pantalla |
| "regla: 404 / 409 / 422" | servicio (la regla); la ruta ya traduce los errores |
| "máximo / único / no repetido" | servicio (chequeo previo) y, si es unicidad, también la base |
| "solo con el permiso X" | ruta (dependencia) y front (la pregunta `can`); si el permiso no existe, migración de permisos |
| "se actualiza sin recargar" | hook: invalidar la caché al terminar la mutación |
| "sin migración" | no tocar el modelo |

---

## Cuándo se toca cada tipo de archivo

Cada capa tiene **una sola responsabilidad**. Para decidir si un archivo entra en tu lista, preguntate qué cambia.

Las direcciones están **desde la raíz del repo** y usan **proveedores** (`supplier`) como ejemplo. Si tu recurso es otro (obra, receta, miembro...), cambiá la palabra y verificá con `ls` o `grep` que el archivo exista.

### Backend

| Archivo (dirección completa) | Qué es | Se toca cuando... | NO se toca cuando... |
|---|---|---|---|
| **Modelo**<br>`backend/app/models/supplier.py` | cómo es la tabla en la base | la consigna agrega, cambia o quita una **columna o tabla** (siempre con migración) | solo se agrega un endpoint, un filtro o una regla |
| **Migración**<br>`backend/alembic/versions/<id>_<nombre>.py` (se genera sola, en esa carpeta) | el cambio de la base, versionado | tocaste un modelo, o hay que dar de alta un **permiso nuevo** | no cambia la base |
| **Schema**<br>`backend/app/schemas/supplier.py` | qué datos entran y salen por la API | el dato debe **verse en la respuesta** (`Out`), o el usuario debe **enviarlo** (`Create`/`Update`/cuerpo de un endpoint) | el dato solo se usa por dentro |
| **Repositorio**<br>`backend/app/repositories/supplier.py` (ojo: tiene dos clases, `SupplierRepository` y `SupplierPriceRepository`) | cómo se **leen** los datos | necesitás una **consulta o filtro nuevo** (contar, filtrar, ver inactivos) | solo modificás un valor; o la lectura que necesitás ya existe |
| **Servicio**<br>`backend/app/services/suppliers.py` | las **reglas de negocio** y los cambios | hay una **regla** (404, 409, límites) o una **acción** que modifica datos | solo se lee y se devuelve sin reglas |
| **Ruta**<br>`backend/app/api/routes/suppliers.py` | la puerta de entrada HTTP | hay un **endpoint nuevo**, un **parámetro nuevo** en la URL, o un **campo nuevo a mapear** en la respuesta (función `_supplier_out`) | solo cambia una regla interna que no afecta la entrada ni la salida |
| **Registro de rutas**<br>`backend/app/api/router.py` | registra los archivos de rutas | se crea un **recurso nuevo** con su archivo de rutas | agregás rutas a un recurso que ya existe |
| **Permisos y dependencias**<br>`backend/app/api/deps.py` | el chequeo `requires("x.view", "firm")` | casi nunca: solo si cambia cómo se chequea un permiso | los permisos existentes alcanzan |
| **Seed**<br>`backend/app/db/seed_dev.py` | datos de ejemplo | la consigna pide datos de ejemplo nuevos; si no, **no lo toques** (mucho texto repetido, como `address`, es de otras entidades) | casi siempre |
| **Tests**<br>`backend/tests/test_suppliers_api.py` y `backend/tests/test_suppliers_service.py` | verificación | agregaste o cambiaste comportamiento; y cuando un test existente se rompe porque cambió un catálogo | no se pide |
| **Diagrama de la base**<br>`docs/der.md` | documentación generada | **nunca a mano**: se regenera con `uv run python -m scripts.generate_erd` tras tocar un modelo | no tocaste modelos |

**Dos preguntas que resuelven casi todo:**
1. ¿Es **leer** datos de una forma nueva? → repositorio.
2. ¿Es **decidir o cambiar** algo? → servicio.

### Frontend

| Archivo (dirección completa) | Qué es | Se toca cuando... | NO se toca cuando... |
|---|---|---|---|
| **Tipos**<br>`frontend/src/features/suppliers/types.ts` | la forma de los datos que llegan de la API | la API devuelve un **campo nuevo** o cambia uno | solo cambia la apariencia |
| **Service**<br>`frontend/src/features/suppliers/supplierService.ts` | las llamadas a la API | hay un **endpoint nuevo** o un **parámetro nuevo** que enviar | la llamada ya existe y alcanza |
| **Hook**<br>`frontend/src/features/suppliers/useSuppliers.ts` | consultas y mutaciones (TanStack Query) | hay una **lectura nueva o con filtro** (clave de caché) o una **acción nueva** (mutación) | solo mostrás algo que ya llega |
| **Formulario**<br>`frontend/src/features/suppliers/supplierForm.ts` y `frontend/src/features/suppliers/SupplierFormModal.tsx` | el formulario de alta/edición | el usuario **carga o edita** el dato en un formulario | el dato cambia por una acción propia (un botón, un menú) |
| **Tabla** (desktop)<br>`frontend/src/features/suppliers/SuppliersTable.tsx` | cómo se ve cada elemento en compu | hay un dato o una marca nueva para **mostrar** | no cambia lo que se ve en la lista |
| **Tarjeta** (celular)<br>`frontend/src/features/suppliers/SupplierCard.tsx` | cómo se ve cada elemento en celular | **siempre que toques la tabla**: son dos archivos para lo mismo | idem |
| **Menú de acciones**<br>`frontend/src/features/suppliers/SupplierActionsMenu.tsx` | las acciones por elemento (el "⋯") | hay una **acción nueva** por proveedor; aparece en la tabla, las tarjetas y el detalle | la acción es de la pantalla entera, no de un elemento |
| **Modal de confirmación**<br>`frontend/src/features/suppliers/DeactivateSupplierModal.tsx` (de molde) | pedir confirmación | la acción es delicada o la consigna pide confirmar | la acción es directa (marcar/desmarcar) |
| **Página de la lista**<br>`frontend/src/pages/SuppliersPage.tsx` | arma la pantalla y guarda el estado | hay un **filtro, interruptor, selector** o un estado vacío nuevo | no cambia la pantalla |
| **Página de detalle**<br>`frontend/src/pages/SupplierDetailPage.tsx` | la pantalla de un solo elemento | la consigna pide algo **dentro del detalle** | solo se pide en la lista |
| **Rutas de pantallas**<br>`frontend/src/App.tsx` | qué pantalla va en cada dirección, con su permiso | es una **pantalla nueva** | la pantalla ya existe |
| **Menú lateral**<br>`frontend/src/layout/FirmNavbar.tsx` | los links del menú | es una **pantalla nueva** que necesita link | la pantalla ya existe |

**Dos preguntas para el frontend:**
1. ¿Es **hablar con la API**? → service y hook.
2. ¿Es **lo que ve el usuario**? → componentes y página (acordate de la tabla **y** la tarjeta).

---

## Recetas por tipo de consigna: la cadena completa

Elegí la receta que se parezca a tu consigna y seguila en orden. Cada paso dice el archivo y, cuando corresponde, **la función existente en la que hay que agregar algo**. Si la consigna mezcla tipos (casi siempre), combinás recetas.

### Receta 1. Un dato nuevo que se muestra y se cambia con una acción propia (preferido, valoración, estado)
1. **Modelo** `backend/app/models/supplier.py`: la columna va en la clase `Supplier`, junto a `is_active` (no en `SupplierPrice`). Un booleano obligatorio necesita `server_default`; si la consigna dice "sin valorar", la columna admite nulo. Si hay un `CHECK` (rango), dale **nombre**.
   - Además: revisá los imports de arriba del archivo (`Integer`, `Boolean`, `CheckConstraint`...).
2. **Migración**: generala, leela y, **si hay `CHECK`, agregalo a mano** (Alembic no detecta los `CHECK`). Ver la sección de migración.
3. **Schemas** `backend/app/schemas/supplier.py`: el campo va en `SupplierOut`. **No** en `SupplierCreate` ni `SupplierUpdate`. Si la acción lleva un dato, una clase nueva para el cuerpo. `SupplierDetailOut` hereda de `SupplierOut`: no hace falta tocarla.
4. **Ruta** `backend/app/api/routes/suppliers.py`:
   - **además, en la función `_supplier_out`**: una línea nueva con el campo (`campo=supplier.campo`). Sin esto, el listado y el detalle fallan al armar la respuesta.
5. **Servicio** `backend/app/services/suppliers.py`: la función de la acción. **No** toques `SUPPLIER_FIELDS` ni `create_supplier`: el dato no se carga por formulario.
6. **Ruta** de la acción (misma ruta que el paso 4): decorador con verbo, dirección, código de respuesta y permiso.
7. Probar en `/docs`.
8. **Front**: tipos (`types.ts`, solo en `SupplierOut`; **no** en `SupplierWrite`), service, hook, y donde se muestre o se accione (ver recetas 8 y 9).

### Receta 2. Un dato nuevo que el usuario carga y edita en el formulario (website, email de facturación)
1. **Modelo** y **migración**: igual que en la receta 1.
2. **Schemas**: el campo va en **los tres**: `SupplierCreate`, `SupplierUpdate` y `SupplierOut`. Para un texto opcional, reusá el estilo de los campos vecinos (`Phone`, `Address`: son alias definidos arriba del archivo con `_optional_text(largo)`).
   - Además: el largo máximo tiene que coincidir con el de la columna del modelo.
3. **Servicio** `backend/app/services/suppliers.py`:
   - **además, en `SUPPLIER_FIELDS`**: sumá el nombre del campo. Si no, el `PATCH` lo ignora.
   - **además, en la función `create_supplier`**: parámetro nuevo (con `= None` si es opcional) y pasarlo al construir el `Supplier(...)`. Si no, **todas las altas dan 500** (la ruta pasa todos los campos del schema).
4. **Ruta**: **además, en `_supplier_out`**, la línea del campo.
5. **Front**:
   - `frontend/src/features/suppliers/types.ts`: **además**, en `SupplierOut` **y** en `SupplierWrite`.
   - `frontend/src/features/suppliers/supplierForm.ts`: valores iniciales, validación y el armado del payload.
   - `frontend/src/features/suppliers/SupplierFormModal.tsx`: el campo de texto, con la etiqueta **en español**.
   - Donde se muestre: `SuppliersTable.tsx` y `SupplierCard.tsx` (los dos) y `SupplierDetailPage.tsx`.

### Receta 3. Un filtro opcional en el listado (?preferred=, ?min_rating=)
1. **Repositorio** `backend/app/repositories/supplier.py`, clase `SupplierRepository`:
   - **además, en el método `entries()`**: parámetro nuevo con valor por defecto, y la condición. La subconsulta `price_count` **no se toca**; el filtro va en la consulta principal.
2. **Ruta** `backend/app/api/routes/suppliers.py`:
   - **además, en la función `list_suppliers`**: el parámetro **en la firma** (con sus límites si el valor tiene rango: eso da el 422 solo) y pasarlo por nombre a `entries(...)`.
3. **Front**:
   - `supplierService.ts`: **además, en `fetchSuppliers`**: parámetro con valor por defecto y enviarlo en la llamada (`params`).
   - `useSuppliers.ts`: **además, en `useSuppliers`**: parámetro con valor por defecto, pasarlo a `fetchSuppliers`, y la clave de caché `[...supplierKeys.all(firmId), "list", filtro]`.
   - `SuppliersPage.tsx`: un estado (`useState`) para el filtro, pasárselo al hook, el control (switch o selector) y revisar **las condiciones de lista vacía** (ver la sección de páginas).

### Receta 4. Una acción nueva sobre un elemento (marcar, reactivar, aprobar, valorar)
1. **Servicio**: función con el orden de siempre: buscar (`get_supplier`, o una lectura de inactivos si corresponde) → error de "no encontrado" → reglas → cambiar → `flush`.
2. **Ruta**: decorador con el **verbo** (POST si cambia algo; PUT si fija un valor), la **dirección** (`/{supplier_id}/accion`), `status_code=204` y el permiso (`MANAGE`). Dentro: `with _supplier_rules():`, la llamada al servicio y `db.commit()`.
   - Si la acción lleva datos: schema de cuerpo y **recibirlo como parámetro** de la función (un parámetro suelto se lee de la URL, no del cuerpo).
3. **Front, service**: la función con el **mismo verbo y la misma dirección** que la ruta, y el cuerpo con la **misma clave** que el schema.
4. **Front, hook**: mutación copiada de una existente, con `useRefresh`. Si recibe más de un dato, agruparlos en un objeto.
5. **Front, `SupplierActionsMenu.tsx`**: **además**, los hooks arriba (antes del `if (!can(...)) return null`) y un ítem nuevo en el menú.

### Receta 5. Una regla de negocio (409, máximo, único, no repetido)
1. **Servicio**: el chequeo va **después** de buscar y **antes** de cambiar. El mensaje de error: una constante arriba del archivo, como `SUPPLIER_NAME_TAKEN`.
2. **Repositorio**: si la regla cuenta o busca algo que hoy no se puede leer, un método **nuevo** (cuenta de elementos activos del mismo estudio). Si solo comparás con un registro que ya leíste, no hace falta.
3. **Ruta**: **no se toca**. `_supplier_rules()` ya traduce `SupplierError` a 409 y `SupplierNotFoundError` a 404. Si definís un tipo de error **nuevo**, hay que agregarlo a esa traducción.
4. **Casos borde que la consigna suele pedir**: qué pasa si el estado **ya es el pedido** (marcar al que ya está marcado: sin error y **sin contar** contra el límite) y qué pasa en el límite exacto (3 permitidos, el cuarto rechazado).
5. **Front**: el mensaje del 409 se muestra con el `detail` del backend (`apiErrorMessage`). Hay que mostrarlo en pantalla, no solo en la consola.

### Receta 6. Un permiso nuevo
1. **Migración a mano**: copiá `backend/alembic/versions/e7b2c5a93f68_seed_supplier_permissions.py`. El `down_revision` es lo que imprime `uv run alembic heads`.
2. **Ruta**: **además**, en el decorador, la dependencia del permiso nuevo (como `MANAGE`/`VIEW`, pero con el permiso nuevo).
3. **Front**: `can("el.permiso")` donde se muestre el botón o la pantalla.
4. **Tests**: es probable que fallen `test_rbac_catalog_seed.py` o `test_route_permissions.py` porque el catálogo cambió. Entender por qué es parte del ejercicio.

### Receta 7. Un recurso nuevo completo (una tabla nueva con su pantalla)
1. **Modelo** nuevo (con `firm_id`, `is_active`; FK compuesta `(<padre>_id, firm_id)` si cuelga de otra tabla) y **migración**.
2. **Repositorio**: clase nueva que hereda de `FirmScopedRepository`.
3. **Servicio**, **schemas**, **ruta**.
   - **Además, en `backend/app/api/router.py`**: el `import` del archivo de rutas y su `include_router(...)`. Sin esto, la ruta no existe.
4. **Front**: carpeta nueva en `frontend/src/features/<recurso>/` con tipos, service, hook, formulario, modales, tabla y tarjeta; página en `frontend/src/pages/`.
   - **Además, en `frontend/src/App.tsx`**: la ruta de la pantalla, con su permiso.
   - **Además, en `frontend/src/layout/FirmNavbar.tsx`**: el link en el menú.

### Receta 8. Mostrar un dato en la lista
1. `types.ts`: el campo en `SupplierOut`.
2. `SuppliersTable.tsx`: **además**, un encabezado nuevo (`Table.Th`) **y** la celda correspondiente (`Table.Td`), o una insignia junto al nombre.
3. `SupplierCard.tsx`: **la misma información**, apilada (una línea más). Es **otro archivo**: no se actualiza solo.
4. Probar en el navegador en compu y a 375 px.

### Receta 9. Un control nuevo en la pantalla de detalle
1. `frontend/src/pages/SupplierDetailPage.tsx`:
   - Los hooks van arriba del componente, antes de cualquier `return` anticipado.
   - Mostrarlo solo con `can("supplier.manage")`.
   - El detalle y la lista se refrescan solos: la clave del detalle empieza con la general (`supplierKeys.all`), y `useRefresh` invalida por prefijo.
2. El error del backend se muestra al usuario.

### Receta 10. Ver o reactivar registros dados de baja
1. **Repositorio**: método **nuevo** que usa `self.select(include_inactive=True)` y filtra a los inactivos. No modifiques `get()`: lo usan otras funciones.
2. **Servicio**: usar ese método en vez de `get_supplier`, y chequear las reglas que dependan del estado activo (ej. nombre repetido entre activos).
3. **Ruta** y **front**: igual que la receta 4.

---

## Backend

### Modelo: `backend/app/models/supplier.py`
- Una columna booleana que no puede ser nula necesita valor por defecto en la base, o las filas que ya existen no tienen valor.
- **Cuidado con la clase:** en un archivo de modelos hay varias clases (el proveedor, sus precios...). Cambiá solo la que nombra la consigna. Buscar "donde dice `is_active`" y cambiar todo es la trampa: aparece en todas.
- **Qué cambia en cadena:** si tocás el modelo, **hay que** generar y aplicar una migración. Si el generador dice "no detecto cambios", es porque no guardaste el modelo.

- **Además, en el mismo archivo:** revisá los imports del principio. Una columna nueva puede necesitar `Integer`, `Boolean`, `CheckConstraint`, `String`...
- **Restricciones (`CHECK`):** dales **nombre** y ponelas en la misma clase. El nombre tiene que ser el mismo en la migración.
- Las columnas de solo lectura por la API (que cambian con una acción) igual son columnas del modelo: la diferencia está en los schemas, no acá.

### Migración: carpeta `backend/alembic/versions/`
- Después de generarla, **leela**: tiene que tener solo lo tuyo (una columna en una tabla), con su valor por defecto y su "deshacer".
- Si trae cambios de otras tablas, es ruido: significa que tocaste algún modelo de más (revisá `git status`).
- Aplicala, verificá que modelos y migraciones coinciden, probá deshacer y rehacer, y regenerá el diagrama de la base (`docs/der.md`).

**Comandos de la migración, en este orden** (todos en `backend/`):

| # | Comando | Para qué | Qué tenés que ver |
|---|---|---|---|
| 1 | `uv run alembic revision --autogenerate -m "add <tabla> <campo>"` | Generar la migración desde el modelo | `Generating ... done`. Si dice que no detecta cambios, no guardaste el modelo |
| 2 | *(abrir el archivo nuevo en `alembic/versions/` y leerlo)* | Revisar que tenga solo lo tuyo | Una columna o tabla en `upgrade()` y su inverso en `downgrade()`. Borrá los comentarios `# ### commands auto generated ###` |
| 3 | `uv run alembic upgrade head` | Aplicarla a la base | `Running upgrade ... -> <tu revisión>` |
| 4 | `uv run alembic check` | Verificar que modelos y migraciones coinciden | `No new upgrade operations detected` |
| 5 | `uv run alembic downgrade -1` | Probar que se puede deshacer | `Running downgrade <tu revisión> -> ...` |
| 6 | `uv run alembic upgrade head` | Volver a aplicarla | `Running upgrade ...` otra vez, sin error |
| 7 | `uv run python -m scripts.generate_erd` | Regenerar `docs/der.md` (el CI falla si está desactualizado) | Archivo actualizado; `git status -sb` lo muestra modificado |
| 8 | `uv run alembic current` | Confirmar en qué revisión quedó la base | Tu revisión con `(head)` |

Los pasos 5 y 6 se pueden escribir juntos: `uv run alembic downgrade -1 && uv run alembic upgrade head`. Si el paso 4 dice que hay diferencias o el paso 5 falla, la migración está mal: corregila antes de seguir. Si necesitás una revisión a mano (por ejemplo, un permiso nuevo), `uv run alembic heads` te da el `down_revision`.
- **Qué cambia en cadena:** sin aplicar la migración, la API responde 500 apenas lee la tabla. Si en el navegador ves "no pudimos cargar" y el backend tira un error de columna inexistente, falta este paso.

- **`CHECK` a mano:** Alembic **no detecta** los `CHECK` al autogenerar, aunque estén en el modelo. Si la consigna pide un rango (por ejemplo, 1 a 5), la migración generada solo tendrá `add_column`: tenés que **agregar vos** en `upgrade()` un `op.create_check_constraint(<nombre>, "supplier", "<condición>")`, y en `downgrade()` el `op.drop_constraint(<nombre>, "supplier", type_="check")` (antes de quitar la columna). El nombre y la condición tienen que ser los del modelo. Copiá cómo lo escribe `d6a1f4b82e57_create_supplier_schema.py`.
- `uv run alembic check` **no** verifica los `CHECK`: no confíes en su "No new upgrade operations detected" para eso. Revisá a ojo que modelo y migración digan lo mismo (mismo rango, mismo nombre).
- Una columna con valor por defecto para filas existentes: la migración necesita el `server_default` aunque el modelo lo tenga.

### Schemas: `backend/app/schemas/supplier.py`
- Tres tipos: Create (lo que llega al dar de alta), Update (lo que llega al editar), Out (lo que sale).
- Regla: un campo va en Create/Update **solo si el usuario lo carga en el formulario**. Si cambia con una acción propia, va solo en Out.
- **Qué cambia en cadena (la trampa grande):** la ruta de alta le pasa a la función del servicio **todos** los campos de Create. Si agregás un campo ahí y el servicio no tiene ese parámetro, cada alta falla con 500. Además, si un campo entra por alta o edición, saltea cualquier regla que hayas puesto en una acción aparte (por ejemplo, un máximo).
- Nullable en la base ↔ "o nulo" en el schema. No nulo ↔ sin "o nulo".

- **Además, en el mismo archivo:** la clase `SupplierOut` es la que define lo que ve el front; `SupplierDetailOut` la hereda.
- Si el campo es una nota o un rango, el tipo del schema tiene que reflejarlo (`int | None`, `Annotated[int, Field(ge=1, le=5, strict=True)]`).
- Un cuerpo de endpoint (`PUT`/`POST` con datos) es una clase nueva de este archivo, y la ruta la recibe como parámetro.
- Lo que llega con restricciones (rango, largo, formato) se valida **acá**: Pydantic devuelve el 422 solo. No lo valides en el servicio.

### Repositorio: `backend/app/repositories/supplier.py`
- Solo **lee**. Si necesitás una consulta que no existe, agregá un método nuevo en vez de cambiar uno que usan otros.
- Las lecturas ya filtran por estudio y por activos. Para ver inactivos hay que pedirlo por nombre.
- Un filtro opcional se agrega como parámetro con valor por defecto, así nada de lo que ya llama a ese método se rompe.
- **Antes de editar, verificá dos cosas:** ¿estás en la clase correcta? (hay una del proveedor y otra de los precios, con métodos del mismo nombre). ¿Estás tocando la consulta principal o una subconsulta? Casi siempre es la principal.
- **Qué cambia en cadena:** el nombre del parámetro nuevo tiene que coincidir con el que usa la ruta cuando lo llama.

- **Además, en el mismo archivo:** `SupplierRepository.entries()` es el que arma el listado: ahí se agrega un filtro opcional. `get()` busca un solo proveedor activo.
- Una lectura nueva = método nuevo **dentro de la clase correcta**, con su docstring de una línea como los demás.

### Servicio: `backend/app/services/suppliers.py`
- Decide y modifica. Orden interno, siempre: buscar, si no existe error de "no encontrado", reglas de negocio, recién después cambiar el valor y hacer flush. Nunca commit acá.
- **Primero verificás, después usás.** Usar el objeto antes de chequear que existe da error 500 en vez de 404.
- Para encontrar un registro normal, usá la función de búsqueda que ya existe: ya da 404 para inactivos y de otro estudio. Solo pedí una lectura nueva si necesitás algo distinto (por ejemplo, ver inactivos).
- **Qué cambia en cadena:** si agregás un chequeo que cuenta o busca en el repo, falta ese método en el repo. Y si la función del servicio recibe parámetros nuevos, hay que revisar quién la llama.

- **Además, en el mismo archivo:**
  - `SUPPLIER_FIELDS` (arriba): el conjunto de campos que el `PATCH` puede editar. Un campo de formulario nuevo **se agrega acá**; uno que cambia por acción propia, **no**.
  - `create_supplier(...)`: parámetros del alta. Un campo nuevo del formulario va como parámetro y se pasa al `Supplier(...)`.
  - `update_supplier(...)`: usa `SUPPLIER_FIELDS`.
  - Las constantes de mensaje de error (como `SUPPLIER_NAME_TAKEN`) están arriba del archivo: una regla nueva suma la suya ahí.
- La excepción que lance el servicio tiene que ser una que la ruta sepa traducir. Un `ValueError` común sale como 500.

### Ruta: `backend/app/api/routes/suppliers.py`
- Copiá una ruta parecida y cambiá solo lo necesario: dirección, nombre de la función y función del servicio a la que llama. Mismo permiso, mismo código de respuesta. La ruta es la que confirma los cambios en la base.
- Verbo: POST si cambia algo, GET si solo lee.
- Un parámetro opcional de la URL **se declara en la firma de la función**; después se pasa por nombre a quien lo use. Declarar y usar son dos lugares distintos y se confunden.
- Editá la función existente; **no pegues una copia al lado**: quedan dos con el mismo nombre y manda la última, o la primera, y no sabés cuál.
- **Qué cambia en cadena:**
  - Si agregaste un campo a un schema de salida, la ruta arma la respuesta **a mano** (función de mapeo). Hay que agregar el campo ahí, con el nombre **exacto** del schema a la izquierda y la columna del modelo a la derecha. Si te olvidás, falla o no devuelve el campo.
  - Si hay rutas fijas (como `/summary`) y dinámicas (`/{id}`), las fijas van antes.
  - Un recurso nuevo se registra en el `router.py`.

- **Además, en el mismo archivo:**
  - `_supplier_out(...)`: arma la respuesta **a mano**, campo por campo. Un campo nuevo de salida **se agrega acá**.
  - `list_suppliers(...)`: el listado. Un filtro nuevo se declara en su firma y se pasa a `entries(...)`.
  - `create_supplier(...)` (ruta de alta): hace `**payload.model_dump()`; por eso un campo en `SupplierCreate` obliga a que el servicio lo reciba.
  - `_supplier_rules()`: el bloque que traduce los errores del servicio a 404, 409 y 422.
  - Los imports de `app.schemas.supplier` de arriba: una clase nueva de schema **se agrega a esa lista**.
- **Contrato con el front:** el verbo, la dirección, el código de respuesta y la forma del cuerpo de la ruta son lo que el service del front tiene que copiar exactamente. Anotalos.

### Probar en /docs
Casos mínimos: caso feliz, id inexistente (404), regla violada (409), dato inválido (422), sin permiso (403), sin sesión (401).

---

## Frontend

### Tipos: `frontend/src/features/suppliers/types.ts`
- Si la API devuelve un campo nuevo, sumalo al tipo de salida con el **mismo nombre** que usa el backend.
- **Qué cambia en cadena:** si el nombre no coincide, TypeScript marca error en cada lugar que lo usa. Los errores suelen decir "¿quisiste decir X?": hacele caso.

- **Además, en el mismo archivo:** `SupplierOut` (lo que llega) y `SupplierWrite` (lo que se envía en el alta y la edición). Un campo que cambia por una acción propia va solo en `SupplierOut`; uno de formulario, en los dos.
- Los tipos son `string | null`, `number | null` o `boolean` según el schema del backend: `| None` en Python es `| null` acá.

### Service: `frontend/src/features/suppliers/supplierService.ts`
- Funciones que llaman a la API. Copiá una parecida y cambiá dirección y verbo.
- Un parámetro opcional se **declara** en la función y además hay que **enviarlo** en la llamada a la API. Declararlo y no enviarlo es el error más común: el backend nunca se entera.

- **Además, en el mismo archivo:** `suppliersUrl(firmId)` arma la base de todas las direcciones; las funciones nuevas la reusan.
- La función de la lista (`fetchSuppliers`): un filtro nuevo es un parámetro con valor por defecto y se envía en `params`.
- **Contrato con la ruta:** verbo (`api.get/post/put/patch`), dirección, y la **clave** del cuerpo tienen que ser idénticos a los del backend. Una letra distinta (`/rate` vs `/rating`) da 404.

### Hook: `frontend/src/features/suppliers/useSuppliers.ts`
- La clave de la consulta es la identidad de la caché. Si una lista se pide de dos formas (con filtro y sin filtro), la clave tiene que incluir el filtro, o se pisan.
- **Qué cambia en cadena:** la invalidación después de una mutación funciona por **prefijo**. La clave nueva tiene que **empezar igual** que la clave general de ese recurso; el filtro va al final. No cambies la clave general: otros hooks dependen de ella.
- Cada acción nueva (marcar, reactivar, aprobar) es una mutación: copiá una existente y cambiá nombre y función del service. Al terminar tiene que refrescar la lista.
- Si agregás un parámetro nuevo a un hook de lectura, dale valor por defecto, así las pantallas que ya lo usan siguen andando.

- **Además, en el mismo archivo:**
  - `supplierKeys.all(firmId)`: la clave general. **No se modifica**: la usa `useRefresh` para invalidar todo por prefijo.
  - `useSuppliers(...)`: la lista. Un filtro nuevo es un parámetro con valor por defecto y va al final de la clave: `[...supplierKeys.all(firmId), "list", filtro]`.
  - `useRefresh(firmId)`: la función que refresca. Toda mutación nueva la usa en `onSuccess`.
- Una mutación recibe **un solo argumento**: si necesita dos datos, agrupalos en un objeto.

### Componentes: carpeta `frontend/src/features/suppliers/` (tabla, tarjeta, menú, modales)
- Lo que se ve en la tabla de desktop **se repite** en la tarjeta de mobile. Cada cambio visual son dos archivos.
- Si una acción aparece en un menú compartido por varias pantallas, ponerla **en el menú** la deja disponible en todas sin tocar las demás.
- **Regla de React: los hooks se llaman siempre, antes de cualquier `return` anticipado.** Si hay un "si no tiene permiso, no mostrar nada", los hooks van arriba de eso.
- Si una acción solo debe verla quien tiene un permiso, preguntale al permiso, nunca al rol.
- Un error del backend (409, 422) se muestra al usuario con el mensaje que manda el backend.
- Texto en español, y funciona a 375 px.

- **Además, en estos archivos:**
  - `SupplierActionsMenu.tsx`: las acciones por proveedor. Una acción nueva: hooks arriba del archivo (antes del `return null` del permiso) y un `Menu.Item` nuevo.
  - `SuppliersTable.tsx` y `SupplierCard.tsx`: lo que se ve de cada proveedor. **Siempre los dos.**
  - `SupplierFormModal.tsx` y `supplierForm.ts`: solo si el dato se carga o edita por formulario (valores iniciales, validación y payload).
  - Un modal de confirmación nuevo se copia de `DeactivateSupplierModal.tsx`.

### Páginas: `frontend/src/pages/SuppliersPage.tsx` y `frontend/src/pages/SupplierDetailPage.tsx`
- Cada cosa de la pantalla necesita su estado, y de distinto tipo: un interruptor es un booleano; "qué proveedor abrió un modal" guarda un objeto o nulo. No los confundas.
- El estado se declara **antes** de usarlo (el archivo se lee de arriba hacia abajo).
- Lo que se desestructura de un hook de consulta es lo que **devuelve** (datos, cargando, error). Tu estado propio no va ahí.
- **Qué cambia en cadena cuando agregás un filtro:** pensá todos los casos de lista vacía.
  - "El estudio no tiene nada" y "el filtro no devuelve nada" son casos distintos. El cartel de "todavía no cargaste ninguno" solo vale para el primero.
  - Todo bloque que exige "hay elementos" para mostrarse (el interruptor, las pestañas, las vistas) desaparece cuando el filtro deja la lista vacía, y el usuario no puede volver. Esas condiciones hay que cambiarlas a "hay elementos **o** estoy filtrando".
  - Al revés: una condición que **exige** el filtro activo oculta todo cuando está apagado (el estado normal).
- Revisá cada bloque que usaba la lista: es fácil arreglar uno y olvidarte de los otros dos que tenían la misma condición.
- Pantalla nueva: ruta en `App.tsx` con el permiso, y link en el menú lateral.

- **Además, en estos archivos:**
  - `SuppliersPage.tsx`: la lista. El estado del filtro, el control y **todas** las condiciones que dependen de la lista (cartel de vacío, pestañas, vista de comparar, tabla y tarjetas).
  - `SupplierDetailPage.tsx`: el detalle. Un control nuevo va acá, con sus hooks arriba.
  - Probá siempre los **tres estados**: con datos, vacía sin filtro y vacía con filtro.

### Sintaxis que te trabó (para releer)
- Un "o" en una condición va entre paréntesis cuando se combina con "y".
- Un ternario devuelve **una sola cosa**; si necesitás devolver dos elementos, van agrupados en un fragmento.
- Cada fragmento, paréntesis y llave que se abre tiene su cierre; contalos de adentro hacia afuera.
- Mover un bloque es **cortar y pegar**, no copiar: si copiás, queda duplicado.
- Un comentario dentro del JSX va entre llaves.

---

## Tabla de coherencia entre capas: nombres que tienen que ser idénticos

Cuando algo "no anda y no da error", casi siempre es un nombre distinto entre dos capas. Antes de seguir, verificá cada fila con `grep`.

| Qué | Dónde tiene que ser idéntico |
|---|---|
| **Nombre del campo** | columna del modelo = campo en `SupplierOut` = izquierda y derecha de `_supplier_out` = `types.ts` = lo que muestran la tabla, la tarjeta y el detalle |
| **Dirección, verbo y código de respuesta** | decorador de la ruta = función del service del front (`api.put(url)`) |
| **Cuerpo de un endpoint** | clase de schema del cuerpo = objeto que manda el service del front (la **clave** es la misma) |
| **Parámetro de la URL (`?algo=`)** | firma de `list_suppliers` = parámetro de `entries()` = `params` del service del front = parámetro del hook |
| **Nombre de un `CHECK`** | modelo = migración (`create_check_constraint` y `drop_constraint`) |
| **Rango o valores permitidos** | `CHECK` de la base = schema (Pydantic) = opciones del control en la pantalla |
| **Largo de un texto** | columna `String(n)` = `max_length` del schema = validación del formulario |
| **Clave de caché** | `useSuppliers` empieza con `supplierKeys.all` = prefijo con el que invalida `useRefresh` |
| **Permiso** | dependencia de la ruta (`VIEW`/`MANAGE`) = `can("supplier.manage")` en el front |

**Cómo comprobarlo rápido:** `grep -rn "<nombre-del-campo>" backend/app frontend/src` y revisá que aparezca en todas las capas que tenía que tocar. Si falta alguna, ahí está el olvido.

---

## Qué chequear después de cada archivo

| Archivo | Chequeo |
|---|---|
| Backend (cualquiera) | que el servidor reinicie sin error; formatear y lint al final |
| Migración | leerla; aplicarla; verificar coincidencia con los modelos; deshacer y rehacer |
| Ruta | probarla en /docs con los casos mínimos |
| Frontend (cualquiera) | el chequeo de tipos en la carpeta del front (si hay rojo, no avances) |
| Pantalla | probarla en el navegador, en desktop y a 375 px, en todos los estados (con datos, vacía, filtrada y vacía) |
| Cierre | `git status` (¿hay archivos que no tocaste?) y `git diff` contra main |

Comandos que corren en cada carpeta: todo lo que empieza con `uv` va en `backend/`; todo lo de `npm` y `npx` va en `frontend/`. Si no estás en la carpeta correcta, falla de formas confusas.

---

## Errores que ya te pasaron (para reconocerlos rápido)

| Si ves... | Probablemente... |
|---|---|
| El generador de migraciones no detecta cambios | no tocaste o no guardaste el modelo |
| La API da 500 con "columna inexistente" | modelo cambiado, migración sin aplicar |
| El generador trae cambios de otras tablas | tocaste modelos de más |
| Todas las altas dan 500 | agregaste un campo a Create que el servicio no recibe |
| La respuesta no trae el campo nuevo o falla al armarla | falta el mapeo manual de la ruta, o el nombre no coincide |
| El filtro no hace nada | declaraste el parámetro pero no lo pasaste (en la ruta o en el service del front) |
| Dos funciones con el mismo nombre | pegaste en vez de editar |
| El filtro anda en una lista y en la otra no | cambiaste la tabla pero no las tarjetas, o la clave de caché no incluye el filtro |
| El switch o las pestañas desaparecen al filtrar | la condición exige "hay elementos" |
| Error de hooks en React | hay un hook después de un `return` anticipado |
| TypeScript dice "no existe, ¿quisiste decir X?" | el nombre del campo no coincide con el del backend |
| "declarado pero nunca usado" | declaraste algo y falta conectarlo |
| Prettier reformateó archivos que no tocaste | se corrió sobre toda la carpeta; usar solo tus archivos |
| La acción del front da 404 o 405 | la dirección o el verbo del service no coinciden con la ruta (ej. `/rate` vs `/rating`, POST vs PUT) |
| El valor llega vacío o la API dice "campo requerido" | el dato se declaró como parámetro suelto (se lee de la URL) en vez de un schema de cuerpo |
| El valor fuera de rango no da 422 | la validación está en el servicio en vez del schema, o falta el `strict=True` para rechazar decimales |
| El valor fuera de rango no lo rechaza la base | falta el `CHECK` en la migración (Alembic no lo autogenera), o el rango del modelo es distinto |
| `null` rompe la función del servicio | la firma no admite `None` (`int` en vez de `int | None`) |
| El filtro del listado ignora el parámetro | falta declararlo en la firma de `list_suppliers` o pasarlo a `entries(...)` |
| La acción anda pero la lista no se actualiza | la mutación no usa `useRefresh`, o la clave de la lista no empieza con `supplierKeys.all` |
| Cambié el listado pero el detalle no muestra el dato | falta el campo en `SupplierDetailOut`/`_supplier_out`, o en el tipo del front |
| Todas las altas dan 500 | un campo nuevo en `SupplierCreate` que `create_supplier` del servicio no recibe |
| El `PATCH` no guarda un campo | falta agregarlo a `SUPPLIER_FIELDS` |
| Edité el método pero no cambia nada | estás en la otra clase del repositorio (`SupplierPriceRepository`) o en la subconsulta |

---

## Estrategia de tiempo para el parcial

1. Primero el **camino feliz completo**, de punta a punta (base, backend, front): que el caso normal ande en pantalla.
2. Después las **reglas de negocio** (límites, 409, casos borde).
3. Por último el **pulido**: mobile, textos, mensajes de error, formato.
4. Commiteá cuando cada capa ande, no al final. Si se acaba el tiempo, tenés algo entregable.
5. Dejá siempre 10 minutos para el cierre: formato, lint, build, `git status`.
6. Si algo te traba más de 10 minutos, pasá a otra parte de la consigna y volvé.
