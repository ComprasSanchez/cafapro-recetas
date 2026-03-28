from __future__ import annotations

from app.db.session import session_scope
from app.service.debitos.view_debitos import ViewDebitos
from app.service.recetas.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas.recetas_service import RecetaService


class ListadoDebitosUseCase:
    @staticmethod
    def load_estados() -> list[tuple[int, str]]:
        with session_scope() as s:
            rows = EstadoSeguimientoService.list(s)

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
