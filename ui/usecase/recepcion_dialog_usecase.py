from __future__ import annotations

from datetime import datetime

from app.db.session import session_scope
from app.service.catalogos.obra_social_service import ObraSocialService
from app.service.catalogos.periodo_service import PeriodoService
from app.service.catalogos.prestador_service import PrestadorService
from app.service.recepcion.estado_recepcion_service import EstadoRecepcionService
from app.service.recepcion.recepcion_service import RecepcionService


class RecepcionDialogUseCase:
    @staticmethod
    def list_recepciones(*, include_closed: bool) -> list:
        with session_scope() as s:
            return RecepcionService.list(s, all=include_closed)

    @staticmethod
    def load_create_catalogs() -> tuple[list, list, list, list]:
        with session_scope() as s:
            obras = ObraSocialService.list(s, solo_activas=True)
            periodos = PeriodoService.list(s, solo_activos=True)
            prestadores = PrestadorService.list(s, solo_activos=True)
            estados = EstadoRecepcionService.list(s)

        return obras, periodos, prestadores, estados

    @staticmethod
    def create_recepcion(
        *,
        obra_social_id: int,
        periodo_id: int,
        prestador_id: int,
        estado_recepcion_id: int,
        fecha_presentacion: datetime,
        observaciones: str | None,
        creado_por_usuario_id: int | None,
    ):
        with session_scope() as s:
            return RecepcionService.create(
                s,
                obra_social_id=int(obra_social_id),
                periodo_id=int(periodo_id),
                prestador_id=int(prestador_id),
                estado_recepcion_id=int(estado_recepcion_id),
                fecha_presentacion=fecha_presentacion,
                observaciones=observaciones,
                creado_por_usuario_id=creado_por_usuario_id,
            )
