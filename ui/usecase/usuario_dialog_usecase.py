from __future__ import annotations

from app.application.catalogos_application import CatalogosApplication


class UsuarioDialogUseCase:
    @staticmethod
    def list_roles() -> list:
        return CatalogosApplication.list_roles()

    @staticmethod
    def create_user(*, username: str, password: str, rol_id: int) -> None:
        CatalogosApplication.create_user(
            username=username,
            password=password,
            rol_id=int(rol_id),
        )
