SAR-CODE-001
Estructura Base del Repositorio (Módulo sar/)
sar/
├── main.py                     # Punto de entrada / Bootstrapper de la app SAR
└── src/
     ├── core/                  # Inicialización y ciclo de vida de Playwright
     ├── pages/                 # Page Object Model (POM) para Portales
     ├── storage/               # Capa de persistencia (PostgreSQL + Excel Handler)
     ├── services/              # Servicios de soporte de negocio
     ├── ui/                    # Capa de Interfaz de Usuario (Atomic Design)
     └── paths.py               # Constantes de rutas de archivos relativas
DDL PostgreSQL v1.0
Creación de Esquemas
CREATE SCHEMA sar_seguridad;
CREATE SCHEMA sar_catalogo;
CREATE SCHEMA sar_produccion;
CREATE SCHEMA sar_archivo;
CREATE SCHEMA sar_auditoria;
CREATE SCHEMA sar_configuracion;
CREATE SCHEMA sar_reporte;
Seguridad
Usuario
CREATE TABLE sar_seguridad.usuario
(
    usuario_id BIGSERIAL PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,

    nombre VARCHAR(200) NOT NULL,

    correo VARCHAR(200),

    password_hash VARCHAR(500) NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ
);
Rol
CREATE TABLE sar_seguridad.rol
(
    rol_id BIGSERIAL PRIMARY KEY,

    codigo VARCHAR(30) NOT NULL UNIQUE,

    nombre VARCHAR(100) NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE
);
Usuario Rol
CREATE TABLE sar_seguridad.usuario_rol
(
    usuario_id BIGINT NOT NULL,

    rol_id BIGINT NOT NULL,

    PRIMARY KEY
    (
        usuario_id,
        rol_id
    ),

    FOREIGN KEY (usuario_id)
        REFERENCES sar_seguridad.usuario(usuario_id),

    FOREIGN KEY (rol_id)
        REFERENCES sar_seguridad.rol(rol_id)
);
Módulo
CREATE TABLE sar_seguridad.modulo
(
    modulo_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
Acción
CREATE TABLE sar_seguridad.accion
(
    accion_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(200),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);
Permiso
CREATE TABLE sar_seguridad.permiso
(
    permiso_id BIGSERIAL PRIMARY KEY,
    modulo_id BIGINT NOT NULL,
    accion_id BIGINT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (modulo_id)
        REFERENCES sar_seguridad.modulo(modulo_id) ON DELETE CASCADE,
    FOREIGN KEY (accion_id)
        REFERENCES sar_seguridad.accion(accion_id) ON DELETE CASCADE,
    CONSTRAINT uq_modulo_accion UNIQUE (modulo_id, accion_id)
);
Rol Permiso
CREATE TABLE sar_seguridad.rol_permiso
(
    rol_id BIGINT NOT NULL,
    permiso_id BIGINT NOT NULL,
    PRIMARY KEY (rol_id, permiso_id),
    FOREIGN KEY (rol_id)
        REFERENCES sar_seguridad.rol(rol_id) ON DELETE CASCADE,
    FOREIGN KEY (permiso_id)
        REFERENCES sar_seguridad.permiso(permiso_id) ON DELETE CASCADE
);
Sesión
CREATE TABLE sar_seguridad.sesion
(
    sesion_id BIGSERIAL PRIMARY KEY,

    usuario_id BIGINT NOT NULL,

    equipo_nombre VARCHAR(200),

    equipo_uuid VARCHAR(200),

    ip_equipo VARCHAR(100),

    version_cliente VARCHAR(50),

    fecha_inicio TIMESTAMPTZ NOT NULL,

    ultimo_heartbeat TIMESTAMPTZ,

    estado VARCHAR(30),

    FOREIGN KEY (usuario_id)
        REFERENCES sar_seguridad.usuario(usuario_id)
);
Catálogos
Municipio
CREATE TABLE sar_catalogo.municipio
(
    municipio_id BIGSERIAL PRIMARY KEY,

    codigo_portal VARCHAR(50),

    nombre VARCHAR(200) NOT NULL,

    activo BOOLEAN DEFAULT TRUE
);
Delegación
CREATE TABLE sar_catalogo.delegacion
(
    delegacion_id BIGSERIAL PRIMARY KEY,

    municipio_id BIGINT NOT NULL,

    codigo_portal VARCHAR(300),

    nombre VARCHAR(200) NOT NULL,

    activo BOOLEAN DEFAULT TRUE,

    FOREIGN KEY (municipio_id)
        REFERENCES sar_catalogo.municipio(municipio_id)
);
Concepto
CREATE TABLE sar_catalogo.concepto
(
    concepto_id BIGSERIAL PRIMARY KEY,

    codigo_portal VARCHAR(300),

    nombre VARCHAR(300) NOT NULL,

    activo BOOLEAN DEFAULT TRUE
);
RFC
CREATE TABLE sar_catalogo.rfc
(
    rfc_id BIGSERIAL PRIMARY KEY,

    rfc VARCHAR(13) NOT NULL UNIQUE,

    razon_social VARCHAR(500) NOT NULL,

    calle VARCHAR(500),

    no_exterior VARCHAR(50),

    no_interior VARCHAR(50),

    colonia VARCHAR(300),

    codigo_postal VARCHAR(10),

    localidad VARCHAR(300),

    municipio VARCHAR(300),

    estado VARCHAR(300),

    activo BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    updated_at TIMESTAMPTZ
);
Estado Sistema
CREATE TABLE sar_catalogo.estado_sistema
(
    estado_id BIGSERIAL PRIMARY KEY,

    entidad VARCHAR(100) NOT NULL,

    codigo VARCHAR(50) NOT NULL,

    descripcion VARCHAR(200),

    UNIQUE(entidad,codigo)
);
Orden
CREATE TABLE sar_produccion.orden_generacion
(
    orden_id BIGSERIAL PRIMARY KEY,

    folio VARCHAR(50) NOT NULL UNIQUE,

    descripcion TEXT,

    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    estado_id BIGINT NOT NULL,

    usuario_id BIGINT NOT NULL,

    FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id),

    FOREIGN KEY (usuario_id)
        REFERENCES sar_seguridad.usuario(usuario_id)
);
Grupo Referencia
CREATE TABLE sar_produccion.grupo_referencia
(
    grupo_id BIGSERIAL PRIMARY KEY,

    orden_id BIGINT NOT NULL,

    rfc_id BIGINT NOT NULL,

    concepto_id BIGINT NOT NULL,

    cantidad_solicitada INTEGER NOT NULL,

    cantidad_generada INTEGER DEFAULT 0,

    cantidad_autorizada INTEGER DEFAULT 0,

    cantidad_rechazada INTEGER DEFAULT 0,

    cantidad_expirada INTEGER DEFAULT 0,

    cantidad_facturada INTEGER DEFAULT 0,

    ultimo_consecutivo INTEGER DEFAULT 0,

    estado_id BIGINT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (orden_id)
        REFERENCES sar_produccion.orden_generacion(orden_id),

    FOREIGN KEY (rfc_id)
        REFERENCES sar_catalogo.rfc(rfc_id),

    FOREIGN KEY (concepto_id)
        REFERENCES sar_catalogo.concepto(concepto_id),

    FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id),

    CONSTRAINT uq_grupo
    UNIQUE
    (
        orden_id,
        rfc_id,
        concepto_id
    )
);
CREATE TABLE sar_produccion.solicitud
(
    solicitud_id BIGSERIAL PRIMARY KEY,

    grupo_id BIGINT NOT NULL,

    delegacion_id BIGINT NOT NULL,

    cantidad_solicitada INTEGER NOT NULL,

    cantidad_generada INTEGER DEFAULT 0,

    cantidad_autorizada INTEGER DEFAULT 0,

    cantidad_facturada INTEGER DEFAULT 0,

    consecutivo_inicio INTEGER NOT NULL,

    consecutivo_fin INTEGER NOT NULL,

    ultimo_consecutivo INTEGER DEFAULT 0,

    usuario_asignado BIGINT,

    estado_id BIGINT NOT NULL,

    fecha_asignacion TIMESTAMPTZ,

    fecha_inicio TIMESTAMPTZ,

    fecha_fin TIMESTAMPTZ,

    FOREIGN KEY (grupo_id)
        REFERENCES sar_produccion.grupo_referencia(grupo_id),

    FOREIGN KEY (delegacion_id)
        REFERENCES sar_catalogo.delegacion(delegacion_id),

    FOREIGN KEY (usuario_asignado)
        REFERENCES sar_seguridad.usuario(usuario_id),

    FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id)
);
Referencia
CREATE TABLE sar_produccion.referencia
(
    referencia_id BIGSERIAL PRIMARY KEY,

    grupo_id BIGINT NOT NULL,

    solicitud_id BIGINT NOT NULL,

    consecutivo_grupo INTEGER NOT NULL,

    referencia_portal VARCHAR(100) NOT NULL,

    importe NUMERIC(14,2),

    fecha_generacion TIMESTAMPTZ NOT NULL,

    fecha_vigencia DATE,

    estado_id BIGINT NOT NULL,

    cantidad INTEGER NOT NULL DEFAULT 1,

    porcentaje INTEGER NOT NULL DEFAULT 100,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    FOREIGN KEY (grupo_id)
        REFERENCES sar_produccion.grupo_referencia(grupo_id),

    FOREIGN KEY (solicitud_id)
        REFERENCES sar_produccion.solicitud(solicitud_id),

    FOREIGN KEY (estado_id)
        REFERENCES sar_catalogo.estado_sistema(estado_id),

    CONSTRAINT uq_referencia_grupo
    UNIQUE
    (
        grupo_id,
        consecutivo_grupo
    ),

    CONSTRAINT uq_referencia_portal
    UNIQUE
    (
        referencia_portal
    )
);

-- Factura
CREATE TABLE sar_archivo.factura
(
    factura_id BIGSERIAL PRIMARY KEY,
    referencia_id BIGINT NOT NULL,
    uuid VARCHAR(36) NOT NULL UNIQUE,
    folio VARCHAR(100),
    rfc_emisor VARCHAR(13) NOT NULL,
    fecha_factura TIMESTAMPTZ NOT NULL,
    pdf_path VARCHAR(1000),
    pdf2_path VARCHAR(1000),
    estado VARCHAR(30) NOT NULL,
    FOREIGN KEY (referencia_id)
        REFERENCES sar_produccion.referencia(referencia_id)
);

-- Asignación
CREATE TABLE sar_archivo.asignacion
(
    asignacion_id BIGSERIAL PRIMARY KEY,
    factura_id BIGINT NOT NULL,
    usuario_destino VARCHAR(100) NOT NULL,
    tipo_asignacion VARCHAR(20) NOT NULL,
    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    observaciones TEXT,
    FOREIGN KEY (factura_id)
        REFERENCES sar_archivo.factura(factura_id)
);

-- Evento Sistema (Catálogo)
CREATE TABLE sar_catalogo.evento_sistema
(
    evento_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    descripcion VARCHAR(300)
);

-- Auditoría
-- Auditoria Login
CREATE TABLE sar_auditoria.auditoria_login
(
    login_id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT,
    sesion_id BIGINT,
    fecha_login TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_logout TIMESTAMPTZ,
    ip VARCHAR(100),
    equipo VARCHAR(200),
    FOREIGN KEY (usuario_id) REFERENCES sar_seguridad.usuario(usuario_id),
    FOREIGN KEY (sesion_id) REFERENCES sar_seguridad.sesion(sesion_id)
);

-- Auditoria Evento
CREATE TABLE sar_auditoria.auditoria_evento
(
    evento_auditoria_id BIGSERIAL PRIMARY KEY,
    evento_id BIGINT NOT NULL,
    usuario_id BIGINT,
    sesion_id BIGINT,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    modulo VARCHAR(100) NOT NULL,
    valor_anterior JSONB,
    valor_nuevo JSONB,
    detalle JSONB,
    FOREIGN KEY (evento_id) REFERENCES sar_catalogo.evento_sistema(evento_id),
    FOREIGN KEY (usuario_id) REFERENCES sar_seguridad.usuario(usuario_id),
    FOREIGN KEY (sesion_id) REFERENCES sar_seguridad.sesion(sesion_id)
);

-- Auditoria Error
CREATE TABLE sar_auditoria.auditoria_error
(
    error_id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT,
    sesion_id BIGINT,
    modulo VARCHAR(100) NOT NULL,
    mensaje TEXT NOT NULL,
    stack_trace TEXT,
    fecha TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (usuario_id) REFERENCES sar_seguridad.usuario(usuario_id),
    FOREIGN KEY (sesion_id) REFERENCES sar_seguridad.sesion(sesion_id)
);

-- Índices de Rendimiento
CREATE INDEX IF NOT EXISTS idx_usuario_rol_rol_id ON sar_seguridad.usuario_rol (rol_id);
CREATE INDEX IF NOT EXISTS idx_sesion_usuario_id ON sar_seguridad.sesion (usuario_id);
CREATE INDEX IF NOT EXISTS idx_rol_permiso_permiso_id ON sar_seguridad.rol_permiso (permiso_id);
CREATE INDEX IF NOT EXISTS idx_permiso_modulo_id ON sar_seguridad.permiso (modulo_id);
CREATE INDEX IF NOT EXISTS idx_permiso_accion_id ON sar_seguridad.permiso (accion_id);

CREATE INDEX IF NOT EXISTS idx_grupo_referencia_orden_id ON sar_produccion.grupo_referencia (orden_id);
CREATE INDEX IF NOT EXISTS idx_grupo_referencia_estado_id ON sar_produccion.grupo_referencia (estado_id);
CREATE INDEX IF NOT EXISTS idx_solicitud_grupo_id ON sar_produccion.solicitud (grupo_id);
CREATE INDEX IF NOT EXISTS idx_solicitud_estado_id ON sar_produccion.solicitud (estado_id);
CREATE INDEX IF NOT EXISTS idx_solicitud_usuario_asignado ON sar_produccion.solicitud (usuario_asignado);
CREATE INDEX IF NOT EXISTS idx_referencia_grupo_id ON sar_produccion.referencia (grupo_id);
CREATE INDEX IF NOT EXISTS idx_referencia_solicitud_id ON sar_produccion.referencia (solicitud_id);
CREATE INDEX IF NOT EXISTS idx_referencia_estado_id ON sar_produccion.referencia (estado_id);

CREATE INDEX IF NOT EXISTS idx_archivo_pdf_referencia_id ON sar_archivo.archivo_pdf (referencia_id);
CREATE INDEX IF NOT EXISTS idx_factura_referencia_id ON sar_archivo.factura (referencia_id);
CREATE INDEX IF NOT EXISTS idx_asignacion_factura_id ON sar_archivo.asignacion (factura_id);

CREATE INDEX IF NOT EXISTS idx_auditoria_login_usuario_id ON sar_auditoria.auditoria_login (usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_login_sesion_id ON sar_auditoria.auditoria_login (sesion_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_evento_evento_id ON sar_auditoria.auditoria_evento (evento_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_evento_usuario_id ON sar_auditoria.auditoria_evento (usuario_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_evento_fecha ON sar_auditoria.auditoria_evento (fecha DESC);
CREATE INDEX IF NOT EXISTS idx_auditoria_error_fecha ON sar_auditoria.auditoria_error (fecha DESC);

-- Configuración
-- Parametro Sistema
CREATE TABLE sar_configuracion.parametro_sistema
(
    parametro_id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Localizador Portal
CREATE TABLE sar_configuracion.localizador_portal
(
    localizador_id BIGSERIAL PRIMARY KEY,
    nombre_clave VARCHAR(100) NOT NULL UNIQUE,
    label_visible VARCHAR(200) NOT NULL,
    estrategia_selector VARCHAR(50) NOT NULL,
    valor_selector VARCHAR(500) NOT NULL,
    descripcion VARCHAR(500),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);