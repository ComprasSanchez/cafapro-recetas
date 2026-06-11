from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.api_client import get_client, TIMEOUT_HEAVY

from app.config.settings import settings
from app.service.recetas.tif_logic import base_from_tif_path, build_detalle_context, norm_str
from app.service.recetas.tif_types import ArchivoData, ArchivoDetalleData
from app.service.recetas.tif_types import ProcesarItemIn, _DetalleContext


MOTIVO_DEBITO_RECETA_VENCIDA_ID = 11


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/recepciones{path}"


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
    archivo_by_id: dict[int, ArchivoData]
    detalles_by_archivo: dict[int, list[ArchivoDetalleData]]
    detalle_ctx_by_archivo: dict[int, _DetalleContext]
    asociados_vigentes_archivo_ids: set[int]
    receta_vigente_by_archivo_id: dict[int, tuple[int, int | None, int | None]]
    processed_bases: set[str]
    ref_index: dict[str, dict[int, ArchivoData]]
    receta_index: dict[str, dict[int, ArchivoData]]
    vencido_updates: dict[int, bool] = field(default_factory=dict)


def load_run_context(*, recepcion_id: int) -> TifRunContext:
    resp = get_client().get(_url(f"/{recepcion_id}/tif-context"), timeout=TIMEOUT_HEAVY)
    if resp.status_code == 404:
        raise RuntimeError(f"No existe la recepcion {recepcion_id}")
    resp.raise_for_status()
    d = resp.json()

    prestador_imed = (d.get("prestadorImed") or "").strip()
    if not prestador_imed:
        raise RuntimeError("Prestador.imed esta vacio; no se puede armar key S3.")

    fecha_presentacion_dt = datetime.fromisoformat(str(d.get("fechaPresentacion") or ""))
    if fecha_presentacion_dt.tzinfo is not None:
        fecha_presentacion_dt = fecha_presentacion_dt.replace(tzinfo=None)
    dias_raw = d.get("diasVencimiento")

    return TifRunContext(
        recepcion_id=int(recepcion_id),
        prestador_imed=prestador_imed,
        fecha_presentacion_dt=fecha_presentacion_dt,
        dias_vencimiento=int(dias_raw) if dias_raw is not None else None,
        only_ref_match=bool(d.get("onlyRefMatch", False)),
    )


def load_run_cache(*, recepcion_id: int) -> TifRunCache:
    resp = get_client().get(_url(f"/{recepcion_id}/tif-bundle"), timeout=TIMEOUT_HEAVY)
    if resp.status_code == 404:
        raise RuntimeError(f"No existe la recepcion {recepcion_id}")
    resp.raise_for_status()
    d = resp.json()

    archivos: list[ArchivoData] = [
        ArchivoData(
            archivo_id=int(a["archivoId"]),
            nro_referencia=a.get("nroReferencia") or None,
            nro_receta=a.get("nroReceta") or None,
            fecha=a.get("fecha") or None,
            hora=a.get("hora") or None,
            vencido=bool(a.get("vencido", False)),
        )
        for a in (d.get("archivos") or [])
    ]

    archivo_by_id: dict[int, ArchivoData] = {a.archivo_id: a for a in archivos}

    detalles_by_archivo: dict[int, list[ArchivoDetalleData]] = {}
    for key_str, rows in (d.get("detallesPorArchivo") or {}).items():
        archivo_id = int(key_str)
        detalles_by_archivo[archivo_id] = [
            ArchivoDetalleData(
                archivo_id=archivo_id,
                cod_medic=r.get("codMedic") or None,
                cantidad=int(r.get("cantidad") or 0),
                importe_bruto=str(r.get("importeBruto") or "0"),
            )
            for r in rows
        ]

    ref_index: dict[str, dict[int, ArchivoData]] = {}
    receta_index: dict[str, dict[int, ArchivoData]] = {}
    for archivo in archivos:
        nro_ref = norm_str(archivo.nro_referencia)
        if nro_ref:
            ref_index.setdefault(nro_ref, {})[archivo.archivo_id] = archivo
        nro_receta = norm_str(archivo.nro_receta)
        if nro_receta:
            receta_index.setdefault(nro_receta, {})[archivo.archivo_id] = archivo

    processed_bases: set[str] = set()
    for frente, dorso in (d.get("ubicaciones") or []):
        base_frente = _extract_processed_base_from_location(frente)
        if base_frente:
            processed_bases.add(base_frente)
        base_dorso = _extract_processed_base_from_location(dorso)
        if base_dorso:
            processed_bases.add(base_dorso)

    detalle_ctx_by_archivo: dict[int, _DetalleContext] = {
        archivo_id: build_detalle_context(rows)
        for archivo_id, rows in detalles_by_archivo.items()
    }

    receta_vigente_by_archivo_id: dict[int, tuple[int, int | None, int | None]] = {}
    for key_str, v in (d.get("recetaVigentePorArchivoId") or {}).items():
        archivo_id = int(key_str)
        estado_receta_id = v.get("estadoRecetaId")
        estado_seguimiento_id = v.get("estadoSeguimientoId")
        receta_vigente_by_archivo_id[archivo_id] = (
            int(v["recetaId"]),
            int(estado_receta_id) if estado_receta_id is not None else None,
            int(estado_seguimiento_id) if estado_seguimiento_id is not None else None,
        )

    return TifRunCache(
        archivo_by_id=archivo_by_id,
        detalles_by_archivo=detalles_by_archivo,
        detalle_ctx_by_archivo=detalle_ctx_by_archivo,
        asociados_vigentes_archivo_ids={int(x) for x in (d.get("asociadosVigentesArchivoIds") or [])},
        receta_vigente_by_archivo_id=receta_vigente_by_archivo_id,
        processed_bases=processed_bases,
        ref_index=ref_index,
        receta_index=receta_index,
    )


def update_archivos_vencido(*, estados_by_archivo_id: dict[int, bool]) -> None:
    if not estados_by_archivo_id:
        return
    payload = [{"archivoId": k, "vencido": v} for k, v in estados_by_archivo_id.items()]
    resp = get_client().patch(
        f"{settings.API_CAFAPRO.rstrip('/')}/archivos/vencido-bulk",
        json=payload,
        timeout=TIMEOUT_HEAVY,
    )
    resp.raise_for_status()


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
