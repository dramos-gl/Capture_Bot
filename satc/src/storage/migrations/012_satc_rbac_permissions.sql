-- =============================================================================
-- MIGRACIÓN 012: Definición RBAC Formal para SATC y Trámites por Vivienda
-- Esquema: sar_seguridad
-- Motor: PostgreSQL 16+
-- Base de Datos: db_sar / db_satc
--
-- PRINCIPIOS DE SEGURIDAD (SAR-SEC-001 & SAR-DEV-001):
--   1. REGISTRO FORMAL RBAC: Da de alta el módulo de seguridad 'TRAMITES_VIVIENDA'.
--   2. VINCULACIÓN CON APP_MODULO: Asocia el módulo al AppModulo 'CTRL_R2F'.
--   3. ACCIONES PERMITIDAS: Crea los permisos atómicos:
--      (TRAMITES_VIVIENDA: LEER, CREAR, EDITAR, ELIMINAR, ASIGNAR, EJECUTAR).
--   4. PROVISIÓN DE ROLES: Asigna los permisos a ADMINISTRADOR y OPERADORR2F.
--   5. IDEMPOTENCIA TOTAL: Utiliza ON CONFLICT DO NOTHING.
-- =============================================================================

DO $$
DECLARE
    v_app_modulo_id BIGINT;
    v_modulo_id BIGINT;
    v_rol_admin_id BIGINT;
    v_rol_r2f_id BIGINT;
    v_accion RECORD;
    v_permiso_id BIGINT;
BEGIN
    -- 1. Obtener o asegurar AppModulo CTRL_R2F
    SELECT app_modulo_id INTO v_app_modulo_id 
    FROM sar_seguridad.app_modulo 
    WHERE codigo = 'CTRL_R2F';

    IF v_app_modulo_id IS NULL THEN
        INSERT INTO sar_seguridad.app_modulo (codigo, nombre, activo)
        VALUES ('CTRL_R2F', 'Control de Recibos & Facturas (R2F)', TRUE)
        RETURNING app_modulo_id INTO v_app_modulo_id;
    END IF;

    -- 2. Registrar el Módulo TRAMITES_VIVIENDA en sar_seguridad.modulo
    SELECT modulo_id INTO v_modulo_id
    FROM sar_seguridad.modulo
    WHERE codigo = 'TRAMITES_VIVIENDA';

    IF v_modulo_id IS NULL THEN
        INSERT INTO sar_seguridad.modulo (codigo, nombre, orden, descripcion, activo, app_modulo_id)
        VALUES (
            'TRAMITES_VIVIENDA',
            'Trámites por Vivienda (UPEs)',
            33.0,
            'Gobernanza del ciclo de vida, vigencias y prevención de omisiones fiduciarias por vivienda',
            TRUE,
            v_app_modulo_id
        )
        RETURNING modulo_id INTO v_modulo_id;
    ELSE
        UPDATE sar_seguridad.modulo 
        SET app_modulo_id = v_app_modulo_id, activo = TRUE
        WHERE modulo_id = v_modulo_id;
    END IF;

    -- 3. Obtener Roles Destino
    SELECT rol_id INTO v_rol_admin_id FROM sar_seguridad.rol WHERE codigo = 'ADMINISTRADOR';
    SELECT rol_id INTO v_rol_r2f_id FROM sar_seguridad.rol WHERE codigo = 'OPERADORR2F';

    -- 4. Crear los permisos para cada Acción estándar y vincular a los roles
    FOR v_accion IN (SELECT accion_id, codigo FROM sar_seguridad.accion WHERE activo = TRUE) LOOP
        -- Insertar Permiso si no existe
        INSERT INTO sar_seguridad.permiso (modulo_id, accion_id, activo)
        VALUES (v_modulo_id, v_accion.accion_id, TRUE)
        ON CONFLICT (modulo_id, accion_id) DO NOTHING;

        SELECT permiso_id INTO v_permiso_id 
        FROM sar_seguridad.permiso 
        WHERE modulo_id = v_modulo_id AND accion_id = v_accion.accion_id;

        -- Asignar todos los permisos al rol ADMINISTRADOR
        IF v_rol_admin_id IS NOT NULL AND v_permiso_id IS NOT NULL THEN
            INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
            VALUES (v_rol_admin_id, v_permiso_id)
            ON CONFLICT (rol_id, permiso_id) DO NOTHING;
        END IF;

        -- Asignar LEER, CREAR, EDITAR, EJECUTAR al rol OPERADORR2F
        IF v_rol_r2f_id IS NOT NULL AND v_permiso_id IS NOT NULL THEN
            IF v_accion.codigo IN ('LEER', 'CREAR', 'EDITAR', 'EJECUTAR') THEN
                INSERT INTO sar_seguridad.rol_permiso (rol_id, permiso_id)
                VALUES (v_rol_r2f_id, v_permiso_id)
                ON CONFLICT (rol_id, permiso_id) DO NOTHING;
            END IF;
        END IF;
    END LOOP;

    -- 5. Asegurar vinculación rol-app_modulo
    IF v_rol_admin_id IS NOT NULL AND v_app_modulo_id IS NOT NULL THEN
        INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
        VALUES (v_rol_admin_id, v_app_modulo_id)
        ON CONFLICT (rol_id, app_modulo_id) DO NOTHING;
    END IF;

    IF v_rol_r2f_id IS NOT NULL AND v_app_modulo_id IS NOT NULL THEN
        INSERT INTO sar_seguridad.rol_app_modulo (rol_id, app_modulo_id)
        VALUES (v_rol_r2f_id, v_app_modulo_id)
        ON CONFLICT (rol_id, app_modulo_id) DO NOTHING;
    END IF;

    RAISE NOTICE 'Migración 012 completada con éxito. Módulo TRAMITES_VIVIENDA registrado y vinculado con RBAC.';
END $$;
