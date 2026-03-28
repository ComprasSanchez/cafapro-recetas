from __future__ import annotations

from app.application.debitos_application import DebitosApplication


class ListadoDebitosUseCase:
    @staticmethod
    def load_estados() -> list[tuple[int, str]]:
        return DebitosApplication.load_estados()

    @staticmethod
    def load_debitos(*, recepcion_id: int, fecha_auditoria=None) -> list:
        return DebitosApplication.load_debitos(
            recepcion_id=int(recepcion_id),
            fecha_auditoria=fecha_auditoria,
        )

    @staticmethod
    def update_estado_seguimiento(*, receta_id: int, estado_seguimiento_id: int | None) -> None:
        DebitosApplication.update_estado_seguimiento(
            receta_id=int(receta_id),
            estado_seguimiento_id=int(estado_seguimiento_id) if estado_seguimiento_id is not None else None,
        )

    @staticmethod
    def periodo_label(*, recepcion_id: int) -> str:
        return DebitosApplication.periodo_label(recepcion_id=int(recepcion_id))
