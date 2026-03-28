from __future__ import annotations

from app.db.session import session_scope
from app.service.debitos.motivos_debito_service import MotivosDebitosService


class MotivosDebitosUseCase:
    @staticmethod
    def list_motivos() -> list:
        with session_scope() as s:
            return MotivosDebitosService.list(s)

    @staticmethod
    def create_motivo(*, descripcion: str, lado: str) -> None:
        with session_scope() as s:
            MotivosDebitosService.create(
                s,
                descripcion=descripcion,
                lado=lado,
            )

    @staticmethod
    def toggle_activo(*, motivo_id: int) -> None:
        with session_scope() as s:
            MotivosDebitosService.toggle_activo(s, int(motivo_id))
