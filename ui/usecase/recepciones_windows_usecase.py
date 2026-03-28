from __future__ import annotations

from app.application.recepciones_application import RecepcionesApplication


class RecepcionesWindowsUseCase:
    @staticmethod
    def list_recepciones(*, include_closed: bool) -> list:
        return RecepcionesApplication.list_recepciones(include_closed=include_closed)

    @staticmethod
    def delete_recepcion(*, recepcion_id: int) -> None:
        RecepcionesApplication.delete_recepcion(recepcion_id=int(recepcion_id))

    @staticmethod
    def list_excluidos_by_recepcion(*, recepcion_id: int) -> list:
        return RecepcionesApplication.list_excluidos_by_recepcion(recepcion_id=int(recepcion_id))

    @staticmethod
    def list_periodos() -> list:
        return RecepcionesApplication.list_periodos()

    @staticmethod
    def list_prestadores_resumen(*, periodo_id: int) -> list:
        return RecepcionesApplication.list_prestadores_resumen(periodo_id=int(periodo_id))

    @staticmethod
    def list_recepciones_resumen(*, periodo_id: int, prestador_id: int) -> list:
        return RecepcionesApplication.list_recepciones_resumen(
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
        )

    @staticmethod
    def get_resumen_recepcion(*, recepcion_id: int):
        return RecepcionesApplication.get_resumen_recepcion(recepcion_id=int(recepcion_id))
