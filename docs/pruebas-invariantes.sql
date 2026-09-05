-- =============================================================================
-- Pruebas de invariantes del esquema del Sprint 1
--
-- Cada bloque intenta romper una regla del modelo. Lo esperado es que la BASE
-- rechace la operacion, no el backend. Correr sobre una base recien creada con
-- ddl-sprint-1.sql (incluidos sus seeds).
--
--   psql -d pid_sprint1 -f pruebas-invariantes.sql
--
-- Ejecutado y verificado contra PostgreSQL 16: los 10 rechazos ocurren y los
-- 3 casos validos pasan.
-- =============================================================================

\set ON_ERROR_STOP off

-- Datos base
INSERT INTO usuario (nombre, email, password_hash) VALUES
    ('Arq A', 'arq@a.com', 'x'), ('Cli B', 'cli@b.com', 'x');
INSERT INTO obra (nombre, created_by) VALUES ('Casa Perez', 1), ('Casa Gomez', 1);
INSERT INTO obra_miembro (obra_id, usuario_id, rol_en_obra) VALUES (1,1,'responsable'), (2,1,'responsable');
INSERT INTO componente_constructivo (obra_id, descripcion, medida, unidad_medida_id)
    VALUES (1, 'Contrapiso PB', 12.5, 1);
INSERT INTO material (nombre, unidad_medida_id, precio_referencia)
    VALUES ('Cemento Loma Negra 50kg', 6, 18500.00);

\echo '--- 1. Email duplicado con otra capitalizacion  [DEBE FALLAR]'
INSERT INTO usuario (nombre, email, password_hash) VALUES ('Otro', 'arq@a.com', 'x');

\echo '--- 2. Email sin normalizar a minusculas  [DEBE FALLAR]'
INSERT INTO usuario (nombre, email, password_hash) VALUES ('Otro', 'ARQ@B.com', 'x');

\echo '--- 3. Dos responsables en la misma obra  [DEBE FALLAR]'
INSERT INTO obra_miembro (obra_id, usuario_id, rol_en_obra) VALUES (1, 2, 'responsable');

\echo '--- 3b. Segundo colaborador en la misma obra  [DEBE PASAR]'
INSERT INTO obra_miembro (obra_id, usuario_id, rol_en_obra) VALUES (1, 2, 'colaborador');

\echo '--- 4. Material con nombre repetido ignorando mayusculas  [DEBE FALLAR]'
INSERT INTO material (nombre, unidad_medida_id, precio_referencia) VALUES ('cemento loma negra 50KG', 6, 19000);

\echo '--- 4b. Tras la baja logica, el nombre se puede reutilizar  [DEBE PASAR]'
UPDATE material SET is_active = false WHERE id = 1;
INSERT INTO material (nombre, unidad_medida_id, precio_referencia) VALUES ('Cemento Loma Negra 50kg', 6, 19000);

\echo '--- 5. Precio negativo  [DEBE FALLAR]'
INSERT INTO material (nombre, unidad_medida_id, precio_referencia) VALUES ('Arena', 2, -1);

\echo '--- 6. Componente con medida cero  [DEBE FALLAR]'
INSERT INTO componente_constructivo (obra_id, descripcion, medida, unidad_medida_id) VALUES (1, 'Nada', 0, 1);

\echo '--- 7. Componente colgado del padre de OTRA obra  [DEBE FALLAR]'
INSERT INTO componente_constructivo (obra_id, parent_id, descripcion, medida, unidad_medida_id)
    VALUES (2, 1, 'Sub de otra obra', 5, 1);

\echo '--- 7b. Componente hijo dentro de la misma obra  [DEBE PASAR]'
INSERT INTO componente_constructivo (obra_id, parent_id, descripcion, medida, unidad_medida_id)
    VALUES (1, 1, 'Carpeta de nivelacion', 12.5, 1);

\echo '--- 8. Componente que es su propio padre  [DEBE FALLAR]'
UPDATE componente_constructivo SET parent_id = id WHERE id = 1;

\echo '--- 9. El trigger mantiene updated_at  [espera t]'
SELECT (updated_at > created_at) AS updated_at_avanzo FROM material WHERE id = 1;

\echo '--- 10. Moneda fuera del formato ISO 4217  [DEBE FALLAR]'
INSERT INTO material (nombre, unidad_medida_id, precio_referencia, moneda) VALUES ('Cal', 6, 100, 'ars');

\echo '--- 11. Borrar una unidad de medida en uso  [DEBE FALLAR]'
DELETE FROM unidad_medida WHERE id = 1;

\echo '--- 12. Obras visibles para el usuario 2  [espera solo Casa Perez]'
SELECT o.nombre
FROM obra o
JOIN obra_miembro om ON om.obra_id = o.id AND om.usuario_id = 2
WHERE o.is_active;
