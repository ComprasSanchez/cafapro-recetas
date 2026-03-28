from __future__ import annotations

from datetime import datetime

from app.application.recepciones_application import RecepcionesApplication


class RecepcionDialogUseCase:
    @staticmethod
    def list_recepciones(*, include_closed: bool) -> list:
        return RecepcionesApplication.list_recepciones(include_closed=include_closed)

    @staticmethod
    def load_create_catalogs():
        return RecepcionesApplication.load_create_catalogs()

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
        return RecepcionesApplication.create_recepcion(
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion_id=int(estado_recepcion_id),
            fecha_presentacion=fecha_presentacion,
            observaciones=observaciones,
            creado_por_usuario_id=creado_por_usuario_id,
        )
