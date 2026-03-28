from __future__ import annotations

from app.db.session import session_scope
from app.service.auditoria.excluidos_service import ExcluidosService
from app.service.catalogos.periodo_service import PeriodoService
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recepcion.view_resumen_recepcion_service import ViewResumenRecepcionService


class RecepcionesWindowsUseCase:
    @staticmethod
    def list_recepciones(*, include_closed: bool) -> list:
        with session_scope() as s:
            return RecepcionService.list(s, all=include_closed)

    @staticmethod
    def delete_recepcion(*, recepcion_id: int) -> None:
        with session_scope() as s:
            RecepcionService.delete(s, int(recepcion_id))

    @staticmethod
    def list_excluidos_by_recepcion(*, recepcion_id: int) -> list:
        with session_scope() as s:
            return ExcluidosService.list_by_recepcion(s, int(recepcion_id))

    @staticmethod
    def list_periodos() -> list:
        with session_scope() as s:
            return list(PeriodoService.list(s))

    @staticmethod
    def list_prestadores_resumen(*, periodo_id: int) -> list:
        with session_scope() as s:
            return ViewResumenRecepcionService.list_prestadores_resumen(
                s,
                periodo_id=int(periodo_id),
            )

    @staticmethod
    def list_recepciones_resumen(*, periodo_id: int, prestador_id: int) -> list:
        with session_scope() as s:
            return RecepcionService.list_recepciones(
                s,
                periodo_id=int(periodo_id),
                prestador_id=int(prestador_id),
            )

    @staticmethod
    def get_resumen_recepcion(*, recepcion_id: int):
        with session_scope() as s:
            return ViewResumenRecepcionService.get_resumen_recepcion(
                s,
                recepcion_id=int(recepcion_id),
            )
