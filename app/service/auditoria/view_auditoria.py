from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class AuditoriaRow:
    row_id: int
    archivo_id: Optional[int]
    asociacion_id: Optional[int]
    receta_id: Optional[int]
    recepcion_id: Optional[int]
    numero_receta: Optional[str]
    numero_referencia: Optional[str]
    nro_lote: Optional[int]
    existe_archivo: bool
    existe_receta: bool
    importe_reconocido: object
    importe_oficial: object
    estado_receta_id: Optional[int]
    estado_receta: Optional[str]
    frente_jpg: Optional[str]
    flag_debitos: bool
    tiene_asoc_en_esta_recepcion: bool
    tiene_asoc_en_otra_recepcion: bool


def _base(recepcion_id: int) -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{recepcion_id}"


def _to_row(r: dict) -> AuditoriaRow:
    return AuditoriaRow(
        row_id=r.get("rowId") or 0,
        archivo_id=r.get("archivoId"),
        asociacion_id=r.get("asociacionId"),
        receta_id=r.get("recetaId"),
        recepcion_id=r.get("recepcionId"),
        numero_receta=r.get("numeroReceta"),
        numero_referencia=r.get("numeroReferencia"),
        nro_lote=r.get("nroLote"),
        existe_archivo=bool(r.get("existeArchivo", False)),
        existe_receta=bool(r.get("existeReceta", False)),
        importe_reconocido=r.get("importeReconocido") or 0,
        importe_oficial=r.get("importeOficial") or 0,
        estado_receta_id=r.get("estadoRecetaId"),
        estado_receta=r.get("estadoReceta"),
        frente_jpg=r.get("frenteJpg"),
        flag_debitos=bool(r.get("flagDebitos", False)),
        tiene_asoc_en_esta_recepcion=bool(r.get("tieneAsocEnEstaRecepcion", False)),
        tiene_asoc_en_otra_recepcion=bool(r.get("tieneAsocEnOtraRecepcion", False)),
    )


class ViewAuditoriaService:
    @staticmethod
    def list(recepcion_id: int) -> list[AuditoriaRow]:
        resp = get_client().get(f"{_base(recepcion_id)}/auditoria")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [_to_row(r) for r in resp.json()]

    @staticmethod
    def list_sin_asociacion(recepcion_id: int) -> list[AuditoriaRow]:
        resp = get_client().get(f"{_base(recepcion_id)}/archivos-sin-asociacion")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [_to_row(r) for r in resp.json()]

    @staticmethod
    def list_archivos_reasociables(recepcion_id: int) -> list[AuditoriaRow]:
        resp = get_client().get(f"{_base(recepcion_id)}/archivos-reasociables")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [_to_row(r) for r in resp.json()]
