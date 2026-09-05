-- =============================================================================
-- Proyecto Integral de Desarrollo (UCAio) — Esquema de referencia del Sprint 1
-- PostgreSQL 15+
--
-- Este archivo es la ESPECIFICACION del modelo, no el mecanismo de despliegue:
-- el esquema real se crea con Alembic. Sirve para (a) discutirlo en equipo,
-- (b) validar que lo que genera `alembic revision --autogenerate` coincide,
-- (c) levantar una base descartable para probar queries a mano.
--
-- Documento asociado: modelo-datos-sprint-1.md
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 0. Utilidad: mantener updated_at desde la base, no desde el ORM.
--    Vale tambien para los UPDATE hechos a mano o desde una migracion.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- -----------------------------------------------------------------------------
-- 1. rol  (HU-1, HU-2) — catalogo cerrado, se carga por seed
-- -----------------------------------------------------------------------------
CREATE TABLE rol (
    id          BIGINT       GENERATED ALWAYS AS IDENTITY,
    codigo      VARCHAR(30)  NOT NULL,
    nombre      VARCHAR(60)  NOT NULL,
    descripcion TEXT,
    CONSTRAINT pk_rol PRIMARY KEY (id),
    CONSTRAINT uq_rol_codigo UNIQUE (codigo)
);

COMMENT ON COLUMN rol.codigo IS 'Valor que usa el codigo fuente: admin | arquitecto | cliente. Nunca se muestra crudo en la UI.';


-- -----------------------------------------------------------------------------
-- 2. usuario  (HU-1, HU-2)
-- -----------------------------------------------------------------------------
CREATE TABLE usuario (
    id            BIGINT       GENERATED ALWAYS AS IDENTITY,
    nombre        VARCHAR(120) NOT NULL,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT pk_usuario PRIMARY KEY (id),
    CONSTRAINT ck_usuario_email_formato CHECK (position('@' IN email) > 1),
    CONSTRAINT ck_usuario_email_lower   CHECK (email = lower(email))
);

-- Unicidad case-insensitive y GLOBAL (incluye inactivos): el email es la
-- identidad de login, reusarlo haria ambiguo el reingreso del usuario original.
CREATE UNIQUE INDEX uq_usuario_email_lower ON usuario (lower(email));

CREATE TRIGGER tg_usuario_updated_at
    BEFORE UPDATE ON usuario
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- -----------------------------------------------------------------------------
-- 3. usuario_rol  — N:M. Un usuario puede ser admin y arquitecto a la vez.
-- -----------------------------------------------------------------------------
CREATE TABLE usuario_rol (
    usuario_id  BIGINT      NOT NULL,
    rol_id      BIGINT      NOT NULL,
    asignado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_usuario_rol PRIMARY KEY (usuario_id, rol_id),
    CONSTRAINT fk_usuario_rol_usuario_id FOREIGN KEY (usuario_id)
        REFERENCES usuario (id) ON DELETE CASCADE,
    CONSTRAINT fk_usuario_rol_rol_id FOREIGN KEY (rol_id)
        REFERENCES rol (id) ON DELETE RESTRICT
);

-- La PK ya cubre las busquedas por usuario_id; este indice es para el sentido
-- inverso ("todos los usuarios con rol cliente" -> el desplegable de HU-3).
CREATE INDEX ix_usuario_rol_rol ON usuario_rol (rol_id);


-- -----------------------------------------------------------------------------
-- 4. obra  (HU-3)
-- -----------------------------------------------------------------------------
CREATE TABLE obra (
    id                    BIGINT       GENERATED ALWAYS AS IDENTITY,
    nombre                VARCHAR(150) NOT NULL,
    descripcion           TEXT,
    direccion             VARCHAR(255),
    fecha_estimada_inicio DATE,
    cliente_id            BIGINT,
    created_by            BIGINT       NOT NULL,
    is_active             BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT pk_obra PRIMARY KEY (id),
    CONSTRAINT ck_obra_nombre_no_vacio CHECK (length(btrim(nombre)) > 0),
    CONSTRAINT fk_obra_cliente_id FOREIGN KEY (cliente_id)
        REFERENCES usuario (id) ON DELETE RESTRICT,
    CONSTRAINT fk_obra_created_by FOREIGN KEY (created_by)
        REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE INDEX ix_obra_cliente_id ON obra (cliente_id);

CREATE TRIGGER tg_obra_updated_at
    BEFORE UPDATE ON obra
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- REGLA DE SERVICIO (no la puede garantizar la FK con roles N:M):
-- cliente_id debe apuntar a un usuario que tenga el rol 'cliente'.


-- -----------------------------------------------------------------------------
-- 5. obra_miembro  — control de acceso de HU-3 ("solo veo mis obras")
-- -----------------------------------------------------------------------------
CREATE TABLE obra_miembro (
    obra_id     BIGINT      NOT NULL,
    usuario_id  BIGINT      NOT NULL,
    rol_en_obra VARCHAR(20) NOT NULL DEFAULT 'colaborador',
    fecha_alta  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_obra_miembro PRIMARY KEY (obra_id, usuario_id),
    CONSTRAINT ck_obra_miembro_rol_valido CHECK (rol_en_obra IN ('responsable', 'colaborador')),
    CONSTRAINT fk_obra_miembro_obra_id FOREIGN KEY (obra_id)
        REFERENCES obra (id) ON DELETE CASCADE,
    CONSTRAINT fk_obra_miembro_usuario_id FOREIGN KEY (usuario_id)
        REFERENCES usuario (id) ON DELETE RESTRICT
);

-- "Mis obras": la query mas frecuente de toda la app.
CREATE INDEX ix_obra_miembro_usuario ON obra_miembro (usuario_id);

-- Una obra tiene a lo sumo un responsable.
CREATE UNIQUE INDEX uq_obra_responsable
    ON obra_miembro (obra_id) WHERE rol_en_obra = 'responsable';


-- -----------------------------------------------------------------------------
-- 6. unidad_medida  (HU-0) — catalogo cerrado, se carga por seed
-- -----------------------------------------------------------------------------
CREATE TABLE unidad_medida (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY,
    codigo      VARCHAR(10) NOT NULL,
    nombre      VARCHAR(60) NOT NULL,
    abreviatura VARCHAR(10) NOT NULL,
    magnitud    VARCHAR(20) NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT pk_unidad_medida PRIMARY KEY (id),
    CONSTRAINT uq_unidad_medida_codigo UNIQUE (codigo),
    CONSTRAINT ck_unidad_medida_magnitud_valida CHECK (
        magnitud IN ('superficie', 'volumen', 'longitud', 'masa', 'conteo')
    )
);

COMMENT ON COLUMN unidad_medida.magnitud IS
    'No lo pide el Sprint 1. Habilita validar conversiones cuando existan las recetas constructivas.';


-- -----------------------------------------------------------------------------
-- 7. material  (HU-4) — catalogo GLOBAL, no por obra
-- -----------------------------------------------------------------------------
CREATE TABLE material (
    id                    BIGINT        GENERATED ALWAYS AS IDENTITY,
    nombre                VARCHAR(200)  NOT NULL,
    unidad_medida_id      BIGINT        NOT NULL,
    precio_referencia     NUMERIC(14,2) NOT NULL,
    moneda                VARCHAR(3)    NOT NULL DEFAULT 'ARS',
    precio_actualizado_en TIMESTAMPTZ,
    is_active             BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_material PRIMARY KEY (id),
    CONSTRAINT ck_material_nombre_no_vacio CHECK (length(btrim(nombre)) > 0),
    CONSTRAINT ck_material_precio_no_negativo CHECK (precio_referencia >= 0),
    CONSTRAINT ck_material_moneda_iso CHECK (moneda ~ '^[A-Z]{3}$'),
    CONSTRAINT fk_material_unidad_medida_id FOREIGN KEY (unidad_medida_id)
        REFERENCES unidad_medida (id) ON DELETE RESTRICT
);

-- Unicidad PARCIAL: solo entre activos. A diferencia del email, el nombre de un
-- material es una etiqueta, no una identidad: si se dio de baja por error, tiene
-- que poder volver a cargarse.
CREATE UNIQUE INDEX uq_material_nombre_activo
    ON material (lower(nombre)) WHERE is_active;

CREATE TRIGGER tg_material_updated_at
    BEFORE UPDATE ON material
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- -----------------------------------------------------------------------------
-- 8. componente_constructivo  (HU-5)
--    parent_id entra desde la primera migracion para la EDT jerarquica futura.
-- -----------------------------------------------------------------------------
CREATE TABLE componente_constructivo (
    id               BIGINT        GENERATED ALWAYS AS IDENTITY,
    obra_id          BIGINT        NOT NULL,
    parent_id        BIGINT,
    descripcion      VARCHAR(255)  NOT NULL,
    medida           NUMERIC(14,3) NOT NULL,
    unidad_medida_id BIGINT        NOT NULL,
    is_active        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT pk_componente_constructivo PRIMARY KEY (id),
    CONSTRAINT ck_componente_constructivo_descripcion_no_vacia CHECK (length(btrim(descripcion)) > 0),
    CONSTRAINT ck_componente_constructivo_medida_positiva CHECK (medida > 0),
    CONSTRAINT ck_componente_constructivo_no_self_parent CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT fk_componente_constructivo_obra_id FOREIGN KEY (obra_id)
        REFERENCES obra (id) ON DELETE CASCADE,
    CONSTRAINT fk_componente_constructivo_unidad_medida_id FOREIGN KEY (unidad_medida_id)
        REFERENCES unidad_medida (id) ON DELETE RESTRICT,
    -- Habilita la FK compuesta de abajo. Redundante con la PK a nivel logico,
    -- necesaria a nivel Postgres para que (parent_id, obra_id) tenga a que apuntar.
    CONSTRAINT uq_componente_id_obra UNIQUE (id, obra_id),
    -- Un componente y su padre pertenecen SIEMPRE a la misma obra. Garantizado
    -- por la base, sin una sola linea de validacion en Python. Como parent_id es
    -- nullable, la restriccion no se evalua en los componentes raiz.
    CONSTRAINT fk_componente_parent FOREIGN KEY (parent_id, obra_id)
        REFERENCES componente_constructivo (id, obra_id) ON DELETE RESTRICT
);

CREATE INDEX ix_componente_obra   ON componente_constructivo (obra_id);
CREATE INDEX ix_componente_parent ON componente_constructivo (parent_id);

CREATE TRIGGER tg_componente_updated_at
    BEFORE UPDATE ON componente_constructivo
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;


-- =============================================================================
-- SEEDS  — en Alembic van en una migracion de DATOS separada de la de esquema.
-- =============================================================================

BEGIN;

INSERT INTO rol (codigo, nombre, descripcion) VALUES
    ('admin',      'Administrador', 'Gestiona usuarios y accede a toda la configuracion.'),
    ('arquitecto', 'Arquitecto',    'Crea y administra obras, materiales y componentes.'),
    ('cliente',    'Cliente',       'Comitente de una obra; consulta su avance.');

INSERT INTO unidad_medida (codigo, nombre, abreviatura, magnitud) VALUES
    ('m2',    'Metro cuadrado', 'm2',    'superficie'),
    ('m3',    'Metro cubico',   'm3',    'volumen'),
    ('ml',    'Metro lineal',   'ml',    'longitud'),
    ('u',     'Unidad',         'u',     'conteo'),
    ('kg',    'Kilogramo',      'kg',    'masa'),
    ('bolsa', 'Bolsa',          'bolsa', 'conteo'),
    ('lt',    'Litro',          'l',     'volumen');

-- Usuario administrador inicial (HU-1: "existe al menos un admin cargado por seed").
-- El hash de abajo es un PLACEHOLDER: generarlo en la migracion a partir de una
-- variable de entorno y forzar el cambio de contrasena en el primer login.
INSERT INTO usuario (nombre, email, password_hash) VALUES
    ('Administrador', 'admin@example.com', '$2b$12$REEMPLAZAR_POR_HASH_REAL');

INSERT INTO usuario_rol (usuario_id, rol_id)
SELECT u.id, r.id
FROM usuario u
CROSS JOIN rol r
WHERE u.email = 'admin@example.com' AND r.codigo = 'admin';

COMMIT;


-- =============================================================================
-- Consultas de referencia — el filtrado por membresia de HU-3 no es opcional.
-- =============================================================================

-- Listado de obras visibles para el usuario :usuario_id
--
--   SELECT o.id, o.nombre, o.direccion, o.fecha_estimada_inicio,
--          c.nombre AS cliente
--   FROM obra o
--   JOIN obra_miembro om ON om.obra_id = o.id AND om.usuario_id = :usuario_id
--   LEFT JOIN usuario c  ON c.id = o.cliente_id
--   WHERE o.is_active
--   ORDER BY o.created_at DESC;

-- Una obra puntual: si no devuelve fila, el endpoint responde 404 (no 403).
--
--   SELECT o.*
--   FROM obra o
--   JOIN obra_miembro om ON om.obra_id = o.id AND om.usuario_id = :usuario_id
--   WHERE o.id = :obra_id AND o.is_active;

-- Roles del usuario, para embeber en el JWT al hacer login y evitar el JOIN
-- en cada request posterior.
--
--   SELECT r.codigo
--   FROM usuario_rol ur
--   JOIN rol r ON r.id = ur.rol_id
--   WHERE ur.usuario_id = :usuario_id;

-- Desplegable de clientes de HU-3.
--
--   SELECT u.id, u.nombre, u.email
--   FROM usuario u
--   JOIN usuario_rol ur ON ur.usuario_id = u.id
--   JOIN rol r ON r.id = ur.rol_id AND r.codigo = 'cliente'
--   WHERE u.is_active
--   ORDER BY u.nombre;
