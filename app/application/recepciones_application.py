from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.db.session import session_scope
from app.service.auditoria.excluidos_service import ExcluidosService
from app.service.catalogos.obra_social_service import ObraSocialService
from app.service.catalogos.periodo_service import PeriodoService
from app.service.catalogos.prestador_service import PrestadorService
from app.service.integraciones.validators_client import ValidatorsClient
from app.service.recepcion.estado_recepcion_service import EstadoRecepcionService
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recepcion.view_resumen_recepcion_service import ViewResumenRecepcionService
from app.service.debitos.view_debitos import ViewDebitos


@dataclass(frozen=True)
class RecepcionIntegracionContext:
    recepcion_id: int
    numero: int
    validador: str
    nro_prestador: str
    cod_financiador: int | None


@dataclass(frozen=True)
class ValidatorsSyncOut:
    accion: str
    referencias_enviadas: int
    respuesta: dict[str, Any]


class RecepcionesApplication:
    @staticmethod
    def list_recepciones(*, include_closed: bool) -> list:
        with session_scope() as s:
            return RecepcionService.list(s, all=include_closed)

    @staticmethod
    def delete_recepcion(*, recepcion_id: int) -> None:
        with session_scope() as s:
            RecepcionService.delete(s, int(recepcion_id))

    @staticmethod
    def load_create_catalogs():
        obras = ObraSocialService.list(solo_activas=True)
        prestadores = PrestadorService.list(solo_activos=True)
        periodos = PeriodoService.list(solo_activos=True)
        with session_scope() as s:
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

    @staticmethod
    def list_excluidos_by_recepcion(*, recepcion_id: int) -> list:
        with session_scope() as s:
            return ExcluidosService.list_by_recepcion(s, int(recepcion_id))

    @staticmethod
    def list_periodos() -> list:
        return PeriodoService.list()

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

    @staticmethod
    def get_recepcion_integracion_context(*, recepcion_id: int) -> RecepcionIntegracionContext:
        rid = int(recepcion_id)

        with session_scope() as s:
            rows = RecepcionService.list(s, all=True)

        rec = next((x for x in rows if int(x.recepcion_id) == rid), None)
        if not rec:
            raise ValueError("La recepción no existe.")

        return RecepcionIntegracionContext(
            recepcion_id=int(rec.recepcion_id),
            numero=int(rec.numero),
            validador=str(getattr(rec, "validador", "imed") or "imed").strip().lower(),
            nro_prestador=str(getattr(rec, "imed", "") or "").strip(),
            cod_financiador=getattr(rec, "codigo_financiador", None),
        )

    @staticmethod
    def has_debitos_sin_estado_by_recepcion(*, recepcion_id: int) -> bool:
        return ViewDebitos.has_debitos_sin_estado_by_recepcion(recepcion_id=int(recepcion_id))

    @staticmethod
    def incluir_excluir_recetas_en_validador(
        *,
        recepcion_id: int,
        accion: str,
        referencias: list[str],
    ) -> ValidatorsSyncOut:
        if RecepcionesApplication.has_debitos_sin_estado_by_recepcion(recepcion_id=int(recepcion_id)):
            raise ValueError(
                "Hay débitos sin estado de seguimiento en esta recepción. "
                "Resolvelos en Débitos antes de usar Excluidos."
            )

        ctx = RecepcionesApplication.get_recepcion_integracion_context(recepcion_id=int(recepcion_id))

        if ctx.validador != "preserfar":
            raise ValueError("Esta acción solo está habilitada para obras sociales con validador 'preserfar'.")

        if not ctx.nro_prestador:
            raise ValueError("La recepción no tiene prestador.imed configurado.")

        try:
            nro_prestador = int(ctx.nro_prestador)
        except Exception as e:
            raise ValueError("Prestador.imed debe ser numérico para consultar la API de validadores.") from e

        if ctx.cod_financiador is None:
            raise ValueError("La obra social no tiene código financiador configurado.")

        refs_limpias: list[str] = []
        seen: set[str] = set()
        for ref in referencias or []:
            value = str(ref or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            refs_limpias.append(value)

        if not refs_limpias:
            raise ValueError("No hay referencias para enviar.")

        client = ValidatorsClient()
        respuesta = client.incluir_excluir_recetas(
            validador=ctx.validador,
            nro_prestador=nro_prestador,
            cod_financiador=int(ctx.cod_financiador),
            accion=accion,
            referencias=refs_limpias,
        )

        return ValidatorsSyncOut(
            accion=str(accion or "").strip().upper(),
            referencias_enviadas=len(refs_limpias),
            respuesta=respuesta,
        )
