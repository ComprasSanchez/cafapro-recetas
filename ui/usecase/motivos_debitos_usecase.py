from __future__ import annotations

from app.application.debitos_application import DebitosApplication


class MotivosDebitosUseCase:
    @staticmethod
    def list_motivos() -> list:
        return DebitosApplication.list_motivos()

    @staticmethod
    def create_motivo(*, descripcion: str, lado: str) -> None:
        DebitosApplication.create_motivo(
            descripcion=descripcion,
            lado=lado,
        )

    @staticmethod
    def toggle_activo(*, motivo_id: int) -> None:
        DebitosApplication.toggle_motivo_activo(motivo_id=int(motivo_id))
