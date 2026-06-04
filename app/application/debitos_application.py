from __future__ import annotations

from app.service.debitos.motivos_debito_service import MotivosDebitosService
from app.service.debitos.view_debitos import ViewDebitos
from app.service.recetas.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas.recetas_service import RecetaService


class DebitosApplication:
    @staticmethod
    def list_motivos() -> list:
        return MotivosDebitosService.list()

    @staticmethod
    def create_motivo(*, descripcion: str, lado: str) -> None:
        MotivosDebitosService.create(descripcion=descripcion, lado=lado)

    @staticmethod
    def toggle_motivo_activo(*, motivo_id: int) -> None:
        MotivosDebitosService.toggle_activo(int(motivo_id))

    @staticmethod
    def load_estados() -> list[tuple[int, str]]:
        rows = EstadoSeguimientoService.list()
        return [(int(r.estado_seguimiento_id), str(r.descripcion)) for r in rows]

    @staticmethod
    def load_debitos(*, recepcion_id: int, fecha_auditoria=None) -> list:
        return list(
            ViewDebitos.list_debitos(
                recepcion_id=int(recepcion_id),
                fecha_auditoria=fecha_auditoria,
            )
        )

    @staticmethod
    def update_estado_seguimiento(*, receta_id: int, estado_seguimiento_id: int | None) -> None:
        RecetaService.update_estado_seguimiento(
            int(receta_id),
            int(estado_seguimiento_id) if estado_seguimiento_id is not None else None,
        )

    @staticmethod
    def periodo_label(*, recepcion_id: int) -> str:
        return ViewDebitos.get_periodo_label(int(recepcion_id))
