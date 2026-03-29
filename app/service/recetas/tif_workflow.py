from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from core.process_tif import TroquelEstado

from app.db.models import Archivo, ArchivoDetalle
from app.dto.medicamentos_dto import MedicamentoDTO
from app.service.recetas.tif_logic import (
    archivo_ts,
    build_detalle_context,
    esta_vencido,
    evaluate_revision_troqueles,
    evaluate_troqueles,
    norm_str,
    to_render_states,
)
from app.service.recetas.tif_types import (
    ProcesarResumen,
    _MatchResult,
    _ScannedItem,
    _TroquelEval,
    _WorkItem,
)


@dataclass(frozen=True)
class WorkSelectionOut:
    work: list[_WorkItem]
    archivo_ids: list[int]
    revision_items: list[_ScannedItem]
    headers_render_by_work_id: dict[int, set[str]]


def select_work_items(
    *,
    scanned: list[_ScannedItem],
    match: _MatchResult,
    only_ref_match: bool,
    seen_recetas: set[str],
    seen_refs: set[str],
    resumen: ProcesarResumen,
    is_archivo_ya_asociado: Callable[[int], bool],
) -> WorkSelectionOut:
    work: list[_WorkItem] = []
    archivo_ids: list[int] = []
    revision_items: list[_ScannedItem] = []
    headers_render_by_work_id: dict[int, set[str]] = {}

    for x in scanned:
        refs = [norm_str(r) for r in (x.scan.headers or []) if norm_str(r)]

        if not refs:
            resumen.sin_match += 1
            revision_items.append(x)
            continue

        if any(ref in match.duplicated_refs for ref in refs):
            resumen.duplicados += 1
            continue

        archivo: Archivo | None = None
        for ref in refs:
            a = match.ref_to_archivo.get(ref)
            if a is not None:
                archivo = a
                break

        if archivo is None:
            resumen.sin_match += 1
            revision_items.append(x)
            continue

        if is_archivo_ya_asociado(int(archivo.archivo_id)):
            revision_items.append(x)
            continue

        nro_rec = norm_str(getattr(archivo, "nro_receta", None))
        nro_ref = norm_str(getattr(archivo, "nro_referencia", None))

        if only_ref_match:
            if nro_ref and nro_ref in seen_refs:
                revision_items.append(x)
                continue
        else:
            if (nro_rec and nro_rec in seen_recetas) or (nro_ref and nro_ref in seen_refs):
                revision_items.append(x)
                continue

        if not only_ref_match and nro_rec:
            seen_recetas.add(nro_rec)
        if nro_ref:
            seen_refs.add(nro_ref)

        matched_refs_for_archivo: set[str] = set()
        for ref in refs:
            a = match.ref_to_archivo.get(ref)
            if a is None:
                continue
            if int(a.archivo_id) == int(archivo.archivo_id):
                matched_refs_for_archivo.add(ref)

        w_item = _WorkItem(it=x.it, scan=x.scan, archivo_id=int(archivo.archivo_id))
        work.append(w_item)
        headers_render_by_work_id[id(w_item)] = matched_refs_for_archivo
        archivo_ids.append(int(archivo.archivo_id))

    return WorkSelectionOut(
        work=work,
        archivo_ids=archivo_ids,
        revision_items=revision_items,
        headers_render_by_work_id=headers_render_by_work_id,
    )


@dataclass(frozen=True)
class PrecomputeOut:
    revision_work: list[_WorkItem]
    estado_render_by_archivo_id: dict[int, dict[str, TroquelEstado]]
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]]
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]]


def precompute_render_context(
    *,
    work: list[_WorkItem],
    revision_items: list[_ScannedItem],
    headers_render_by_work_id: dict[int, set[str]],
    archivo_by_id: dict[int, Archivo],
    detalles_by_archivo: dict[int, list[ArchivoDetalle]],
    fecha_presentacion_dt: datetime,
    dias_vencimiento: int | None,
    med_cache: dict[str, MedicamentoDTO | None],
    warm_cache: Callable[[set[str]], None],
    resumen: ProcesarResumen,
) -> PrecomputeOut:
    revision_work: list[_WorkItem] = []
    for x in revision_items:
        w_item = _WorkItem(
            it=x.it,
            scan=x.scan,
            archivo_id=0,
        )
        revision_work.append(w_item)
        headers_render_by_work_id[id(w_item)] = set()

    all_codebars: set[str] = set()
    for w in work:
        for cb in (w.scan.troqueles or []):
            cb_value = norm_str(cb)
            if cb_value:
                all_codebars.add(cb_value)

    for w in revision_work:
        for cb in (w.scan.troqueles or []):
            cb_value = norm_str(cb)
            if cb_value:
                all_codebars.add(cb_value)

    warm_cache(all_codebars)

    estado_render_by_archivo_id: dict[int, dict[str, TroquelEstado]] = {}
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]] = {}
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]] = {}

    for w in work:
        archivo = archivo_by_id.get(w.archivo_id)
        if not archivo:
            resumen.errores.append(f"{w.it.file_name}: archivo_id {w.archivo_id} no existe en DB")
            continue

        archivo_ts_value = archivo_ts(archivo)
        esta_vencido_value = esta_vencido(archivo_ts_value, fecha_presentacion_dt, dias_vencimiento)
        if getattr(archivo, "vencido", False) != esta_vencido_value:
            archivo.vencido = esta_vencido_value

        dets = detalles_by_archivo.get(w.archivo_id, [])
        detalle_ctx = build_detalle_context(dets)

        evals = evaluate_troqueles(
            scan_troqueles=(w.scan.troqueles or []),
            detalle=detalle_ctx,
            med_cache=med_cache,
        )

        troquel_evals_by_archivo_id[w.archivo_id] = evals
        troquel_evals_by_work_id[id(w)] = evals
        estado_render_by_archivo_id[w.archivo_id] = to_render_states(evals)

    for w in revision_work:
        evals = evaluate_revision_troqueles(
            scan_troqueles=(w.scan.troqueles or []),
            med_cache=med_cache,
        )
        troquel_evals_by_work_id[id(w)] = evals

    return PrecomputeOut(
        revision_work=revision_work,
        estado_render_by_archivo_id=estado_render_by_archivo_id,
        troquel_evals_by_archivo_id=troquel_evals_by_archivo_id,
        troquel_evals_by_work_id=troquel_evals_by_work_id,
    )
