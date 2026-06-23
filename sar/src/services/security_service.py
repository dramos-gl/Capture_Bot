"""Security service handling authentication, sessions, and granular RBAC checks."""

from typing import Optional, List
from sqlalchemy.orm import Session
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sar.src.storage.repositories import UsuarioRepository, AuditRepository
from sar.src.storage.models import Sesion


class SecurityService:
    """Orchestrates authentication, session registration, and permission validation."""

    def __init__(self, session: Session):
        self.session = session
        self.user_repo = UsuarioRepository(session)
        self.audit_repo = AuditRepository(session)
        self.ph = PasswordHasher()

    def login(
        self,
        username: str,
        password_raw: str,
        ip_equipo: str = "127.0.0.1",
        equipo_nombre: str = "Local PC",
        equipo_uuid: str = "local-uuid"
    ) -> Optional[Sesion]:
        """Authenticates a user, opens a session, and logs the access."""
        user = self.user_repo.get_by_username(username)
        if not user or not user.activo:
            # Registrar intento fallido de error (usuario inexistente o inactivo)
            self.audit_repo.log_error(
                usuario_id=None,
                sesion_id=None,
                modulo="SEGURIDAD",
                mensaje=f"Intento de inicio de sesión fallido para usuario inexistente o inactivo: '{username}'"
            )
            return None

        # Verificar contraseña
        is_valid = False
        
        # Soporte para bypass del placeholder semilla si es necesario
        if "placeholderhashforadmin123" in user.password_hash:
            is_valid = (password_raw == "admin123")
        else:
            try:
                is_valid = self.ph.verify(user.password_hash, password_raw)
            except (VerifyMismatchError, Exception):
                is_valid = False

        if not is_valid:
            # Registrar contraseña incorrecta
            self.audit_repo.log_error(
                usuario_id=user.usuario_id,
                sesion_id=None,
                modulo="SEGURIDAD",
                mensaje=f"Contraseña incorrecta para usuario: '{username}'"
            )
            return None

        # Autenticación exitosa -> Crear sesión
        sesion = self.audit_repo.create_session(
            usuario_id=user.usuario_id,
            equipo_nombre=equipo_nombre,
            equipo_uuid=equipo_uuid,
            ip_equipo=ip_equipo
        )

        # Loguear inicio de sesión físico
        self.audit_repo.log_login(
            usuario_id=user.usuario_id,
            sesion_id=sesion.sesion_id,
            ip=ip_equipo,
            equipo=equipo_nombre
        )

        # Registrar evento transaccional
        self.audit_repo.log_evento(
            evento_codigo="LOGIN_EXITOSO",
            modulo="SEGURIDAD",
            usuario_id=user.usuario_id,
            sesion_id=sesion.sesion_id,
            detalle={"username": username, "status": "Autenticado con éxito"}
        )

        return sesion

    def logout(self, sesion_id: int) -> None:
        """Closes a session and logs the logout event."""
        sesion = self.session.get(Sesion, sesion_id)
        if sesion and sesion.estado == "ACTIVA":
            # Cambiar estado de la sesión
            self.audit_repo.close_session(sesion_id)

            # Registrar salida física
            self.audit_repo.log_logout(
                usuario_id=sesion.usuario_id,
                sesion_id=sesion_id
            )

            # Registrar evento transaccional
            self.audit_repo.log_evento(
                evento_codigo="LOGOUT",
                modulo="SEGURIDAD",
                usuario_id=sesion.usuario_id,
                sesion_id=sesion_id
            )
            self.session.flush()

    def has_permission(self, usuario_id: int, modulo_codigo: str, accion_codigo: str) -> bool:
        """Verifies if the user holds a permission mapped to Modulo + Accion."""
        permissions = self.user_repo.get_user_permissions(usuario_id)
        
        # Buscar la tupla (modulo_codigo, accion_codigo) en la lista de tuplas
        for mod, acc in permissions:
            if mod == modulo_codigo and acc == accion_codigo:
                return True
        return False
