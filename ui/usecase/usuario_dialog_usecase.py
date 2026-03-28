from __future__ import annotations

from app.db.session import session_scope
from app.service.catalogos.rol_service import RolesService
from app.service.catalogos.usuario_service import UsuariosService


class UsuarioDialogUseCase:
    @staticmethod
    def list_roles() -> list:
        with session_scope() as s:
            return RolesService.list(s)

    @staticmethod
    def create_user(*, username: str, password: str, rol_id: int) -> None:
        with session_scope() as s:
            UsuariosService.create(
                s,
                username=username,
                password=password,
                rol_id=int(rol_id),
            )
