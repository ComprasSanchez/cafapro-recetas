from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from app.db.models import Archivo, ArchivoDetalle
from app.service.recetas.tif_logic import base_from_tif_path, build_detalle_context, is_valesalud, norm_str
from app.service.recetas.tif_types import ProcesarItemIn, _DetalleContext


MOTIVO_DEBITO_RECETA_VENCIDA_ID = 11


@dataclass(frozen=True)
class TifRunContext:
    recepcion_id: int
    prestador_imed: str
    fecha_presentacion_dt: datetime
    dias_vencimiento: int | None
    only_ref_match: bool
    motivo_debito_receta_vencida_id: int = MOTIVO_DEBITO_RECETA_VENCIDA_ID


@dataclass
class TifRunCache:
    archivo_by_id: dict[int, Archivo]
    detalles_by_archivo: dict[int, list[ArchivoDetalle]]
    detalle_ctx_by_archivo: dict[int, _DetalleContext]
    asociados_vigentes_archivo_ids: set[int]
    receta_vigente_by_archivo_id: dict[int, tuple[int, int | None, int | None]]
    processed_bases: set[str]
    ref_index: dict[str, dict[int, Archivo]]
    receta_index: dict[str, dict[int, Archivo]]
    vencido_updates: dict[int, bool] = field(default_factory=dict)


def load_run_context(session: Session, *, recepcion_id: int) -> TifRunContext:
    rec = TifRepository.get_recepcion(session, recepcion_id=int(recepcion_id))
    if not rec:
        raise RuntimeError(f"No existe la recepcion {recepcion_id}")

    pr_row = TifRepository.get_prestador(session, prestador_id=int(rec.prestador_id))
    if not pr_row:
        raise RuntimeError("No existe el prestador asociado a la recepcion.")

    prestador_imed = (getattr(pr_row, "imed", "") or "").strip()
    if not prestador_imed:
        raise RuntimeError("Prestador.imed esta vacio; no se puede armar key S3.")

    fecha_presentacion = rec.fecha_presentacion
    if isinstance(fecha_presentacion, datetime):
        fecha_presentacion_dt = fecha_presentacion
    else:
        fecha_presentacion_dt = datetime.fromisoformat(str(fecha_presentacion))

    os_row = TifRepository.get_obra_social_context(session, obra_social_id=int(rec.obra_social_id))
    os_nombre = os_row[0] if os_row else None
    dias_vencimiento_raw = os_row[1] if os_row else None
    dias_vencimiento = int(dias_vencimiento_raw) if dias_vencimiento_raw is not None else None

    return TifRunContext(
        recepcion_id=int(recepcion_id),
        prestador_imed=prestador_imed,
        fecha_presentacion_dt=fecha_presentacion_dt,
        dias_vencimiento=dias_vencimiento,
        only_ref_match=is_valesalud(os_nombre),
    )


def _extract_processed_base_from_location(path_value: str | None) -> str:
    raw = str(path_value or "").strip()
    if not raw:
        return ""

    normalized = raw.replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    if "_" not in stem:
        return ""

    return norm_str(stem.rsplit("_", 1)[0])


def load_run_cache(session: Session, *, recepcion_id: int) -> TifRunCache:
    archivos, detalles_by_archivo, asociados_vigentes, ubicaciones = TifRepository.load_recepcion_processing_bundle(
        session,
        recepcion_id=int(recepcion_id),
    )
    receta_vigente_by_archivo_id = TifRepository.load_vigente_receta_by_archivo(
        session,
        recepcion_id=int(recepcion_id),
    )

    archivo_by_id: dict[int, Archivo] = {
        int(a.archivo_id): a for a in archivos
    }

    ref_index: dict[str, dict[int, Archivo]] = {}
    receta_index: dict[str, dict[int, Archivo]] = {}

    for archivo in archivos:
        archivo_id = int(archivo.archivo_id)

        nro_ref = norm_str(getattr(archivo, "nro_referencia", None))
        if nro_ref:
            ref_index.setdefault(nro_ref, {})[archivo_id] = archivo

        nro_receta = norm_str(getattr(archivo, "nro_receta", None))
        if nro_receta:
            receta_index.setdefault(nro_receta, {})[archivo_id] = archivo

    processed_bases: set[str] = set()
    for frente, dorso in ubicaciones:
        base_frente = _extract_processed_base_from_location(frente)
        if base_frente:
            processed_bases.add(base_frente)

        base_dorso = _extract_processed_base_from_location(dorso)
        if base_dorso:
            processed_bases.add(base_dorso)

    normalized_detalles = {
        int(archivo_id): rows
        for archivo_id, rows in detalles_by_archivo.items()
    }

    detalle_ctx_by_archivo: dict[int, _DetalleContext] = {
        int(archivo_id): build_detalle_context(rows)
        for archivo_id, rows in normalized_detalles.items()
    }

    return TifRunCache(
        archivo_by_id=archivo_by_id,
        detalles_by_archivo=normalized_detalles,
        detalle_ctx_by_archivo=detalle_ctx_by_archivo,
        asociados_vigentes_archivo_ids={int(x) for x in asociados_vigentes},
        receta_vigente_by_archivo_id={
            int(archivo_id): (int(receta_id), estado_receta_id, estado_seguimiento_id)
            for archivo_id, (receta_id, estado_receta_id, estado_seguimiento_id)
            in receta_vigente_by_archivo_id.items()
        },
        processed_bases=processed_bases,
        ref_index=ref_index,
        receta_index=receta_index,
    )


def filter_unprocessed_items(
    *,
    items: list[ProcesarItemIn],
    run_cache: TifRunCache,
) -> tuple[list[ProcesarItemIn], int]:
    items_filtrados: list[ProcesarItemIn] = []
    ya_asociado = 0

    for it in items:
        base_name = base_from_tif_path(it.full_path)
        if base_name and base_name in run_cache.processed_bases:
            ya_asociado += 1
            continue
        items_filtrados.append(it)

    return items_filtrados, ya_asociado
