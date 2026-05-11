from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Callable

from core.process_tif import TroquelEstado
from core.process_tif import TiffProcessor
from sqlalchemy.orm import Session

from app.db.models import Archivo, ArchivoDetalle
from app.dto.medicamentos_dto import MedicamentoDTO
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.service.recetas.tif_context import TifRunCache, TifRunContext
from app.service.recetas.tif_logic import (
    archivo_ts,
    build_detalle_context,
    esta_vencido,
    evaluate_revision_troqueles,
    evaluate_troqueles,
    match_all_refs_cached,
    norm_str,
    ref_candidates,
    to_render_states,
    warm_medicamento_cache,
)
from app.service.recetas.tif_parallel import parallel_render_upload, parallel_scan, scan_one_item
from app.service.recetas.tif_persistence import filter_valid_uploaded, persist_uploaded_chunk
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
    ProcesarStats,
    _DetalleContext,
    _MatchResult,
    _ScannedItem,
    _TroquelEval,
    _WorkItem,
)


StageProgressCb = Callable[[int, int, float, str], None]
ProcessStageCb = Callable[[str, float], None]


def _chunks(lst: list[ProcesarItemIn], size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


@dataclass(frozen=True)
class WorkSelectionOut:
    work: list[_WorkItem]
    archivo_ids: list[int]
    revision_items: list[_ScannedItem]
    headers_render_by_work_id: dict[int, set[str]]
    revision_reason_by_item_id: dict[int, str]


def _append_revision_sample(
    resumen: ProcesarResumen,
    *,
    it: ProcesarItemIn,
    reason: str,
    refs: list[str],
) -> None:
    if len(resumen.revision_muestras) >= 20:
        return

    token = ", ".join(refs[:3]) if refs else "-"
    resumen.revision_muestras.append(
        f"{it.file_name} | {reason} | refs={token}"
    )


def _normalize_header_token(value: str) -> str:
    raw = norm_str(value)
    if not raw:
        return ""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits or raw


def _candidate_archivo_ids(token: str, *, index: dict[str, dict[int, Archivo]]) -> set[int]:
    ids: set[int] = set()
    for cand in ref_candidates(token):
        for archivo_id in index.get(cand, {}):
            ids.add(int(archivo_id))
    return ids


def _resolve_unique_from_headers(
    *,
    refs: list[str],
    index: dict[str, dict[int, Archivo]],
) -> int | None:
    resolved_ids: set[int] = set()

    for ref in refs:
        ids = _candidate_archivo_ids(ref, index=index)
        if len(ids) > 1:
            return None
        if len(ids) == 1:
            resolved_ids.update(ids)
            if len(resolved_ids) > 1:
                return None

    if len(resolved_ids) == 1:
        return next(iter(resolved_ids))
    return None


def _extract_short_long_pair(refs: list[str]) -> tuple[str, str] | None:
    if len(refs) != 2:
        return None

    short_vals = [x for x in refs if len(x) in (12, 13)]
    long_vals = [x for x in refs if len(x) >= 18]
    if len(short_vals) != 1 or len(long_vals) != 1:
        return None

    return short_vals[0], long_vals[0]


def _is_ref_matched_to_archivo(
    *,
    ref: str,
    archivo_id: int,
    ref_index: dict[str, dict[int, Archivo]],
    receta_index: dict[str, dict[int, Archivo]],
    only_ref_match: bool,
) -> bool:
    ref_ids = _candidate_archivo_ids(ref, index=ref_index)
    if archivo_id in ref_ids:
        return True

    if only_ref_match:
        return False

    rec_ids = _candidate_archivo_ids(ref, index=receta_index)
    return archivo_id in rec_ids


def select_work_items(
    *,
    scanned: list[_ScannedItem],
    match: _MatchResult,
    only_ref_match: bool,
    archivo_by_id: dict[int, Archivo],
    ref_index: dict[str, dict[int, Archivo]],
    receta_index: dict[str, dict[int, Archivo]],
    receta_vigente_by_archivo_id: dict[int, tuple[int, int | None, int | None]],
    seen_archivo_ids: set[int],
    asociados_vigentes_iniciales: set[int],
    seen_recetas: set[str],
    seen_refs: set[str],
    resumen: ProcesarResumen,
) -> WorkSelectionOut:
    work: list[_WorkItem] = []
    archivo_ids: list[int] = []
    revision_items: list[_ScannedItem] = []
    headers_render_by_work_id: dict[int, set[str]] = {}
    revision_reason_by_item_id: dict[int, str] = {}

    for x in scanned:
        refs: list[str] = []
        for raw in (x.scan.headers or []):
            token = _normalize_header_token(raw)
            if token:
                refs.append(token)

        if refs:
            resumen.con_header += 1
        else:
            resumen.sin_header += 1

        if not refs:
            resumen.sin_match += 1
            resumen.revision_por_sin_match += 1
            resumen.revision_por_header_vacio += 1
            revision_items.append(x)
            reason = "Sin header"
            revision_reason_by_item_id[id(x)] = reason
            _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
            continue

        if any(ref in match.duplicated_refs for ref in refs):
            resumen.sin_match += 1
            resumen.revision_por_sin_match += 1
            resumen.revision_por_header_sin_match += 1
            revision_items.append(x)
            reason = "Header ambiguo"
            revision_reason_by_item_id[id(x)] = reason
            _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
            continue

        archivo: Archivo | None = None
        archivo_id: int | None = None
        replace_receta_id: int | None = None

        pair = _extract_short_long_pair(refs)
        if pair is not None and not only_ref_match:
            short_ref, long_ref = pair
            receta_ids = _candidate_archivo_ids(long_ref, index=receta_index)
            referencia_ids = _candidate_archivo_ids(short_ref, index=ref_index)
            if len(receta_ids) == 1 and len(referencia_ids) == 1:
                receta_id = next(iter(receta_ids))
                referencia_id = next(iter(referencia_ids))
                if receta_id == referencia_id:
                    archivo_id = receta_id

        if archivo_id is None and not only_ref_match:
            archivo_id = _resolve_unique_from_headers(refs=refs, index=receta_index)

        if archivo_id is None:
            archivo_id = _resolve_unique_from_headers(refs=refs, index=ref_index)

        if archivo_id is not None:
            archivo = archivo_by_id.get(int(archivo_id))

        if archivo is None:
            resumen.sin_match += 1
            resumen.revision_por_sin_match += 1
            resumen.revision_por_header_sin_match += 1
            revision_items.append(x)
            reason = "Header sin match"
            revision_reason_by_item_id[id(x)] = reason
            _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
            continue

        if int(archivo.archivo_id) in seen_archivo_ids:
            revision_items.append(x)
            resumen.duplicados += 1
            if only_ref_match:
                resumen.revision_por_duplicado_lote_ref += 1
                reason = "Duplicado en lote (ref)"
            else:
                resumen.revision_por_duplicado_lote_receta += 1
                reason = "Duplicado en lote (receta)"
            revision_reason_by_item_id[id(x)] = reason
            _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
            continue

        if int(archivo.archivo_id) in asociados_vigentes_iniciales:
            vigente_info = receta_vigente_by_archivo_id.get(int(archivo.archivo_id))
            if vigente_info is not None:
                prev_receta_id, prev_estado_receta_id, prev_estado_seguimiento_id = vigente_info
                if (
                    int(prev_receta_id) > 0
                    and int(prev_estado_receta_id or 0) == 1
                    and int(prev_estado_seguimiento_id or 0) == 3
                ):
                    replace_receta_id = int(prev_receta_id)

            if replace_receta_id is None:
                resumen.revision_por_ya_asociado += 1
                revision_items.append(x)
                reason = "Ya asociado"
                revision_reason_by_item_id[id(x)] = reason
                _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
                continue

        nro_rec = norm_str(getattr(archivo, "nro_receta", None))
        nro_ref = norm_str(getattr(archivo, "nro_referencia", None))

        if only_ref_match:
            if nro_ref and nro_ref in seen_refs:
                revision_items.append(x)
                resumen.duplicados += 1
                resumen.revision_por_duplicado_lote_ref += 1
                reason = "Duplicado en lote (ref)"
                revision_reason_by_item_id[id(x)] = reason
                _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
                continue
        else:
            ref_dup = bool(nro_ref and nro_ref in seen_refs)
            rec_dup = bool(nro_rec and nro_rec in seen_recetas)
            if rec_dup or ref_dup:
                revision_items.append(x)
                resumen.duplicados += 1
                if rec_dup:
                    resumen.revision_por_duplicado_lote_receta += 1
                if ref_dup:
                    resumen.revision_por_duplicado_lote_ref += 1
                reason = "Duplicado en lote (receta)" if rec_dup else "Duplicado en lote (ref)"
                revision_reason_by_item_id[id(x)] = reason
                _append_revision_sample(resumen, it=x.it, reason=reason, refs=refs)
                continue

        if not only_ref_match and nro_rec:
            seen_recetas.add(nro_rec)
        if nro_ref:
            seen_refs.add(nro_ref)
        seen_archivo_ids.add(int(archivo.archivo_id))

        matched_refs_for_archivo: set[str] = set()
        for ref in refs:
            if _is_ref_matched_to_archivo(
                ref=ref,
                archivo_id=int(archivo.archivo_id),
                ref_index=ref_index,
                receta_index=receta_index,
                only_ref_match=only_ref_match,
            ):
                matched_refs_for_archivo.add(ref)

        w_item = _WorkItem(
            it=x.it,
            scan=x.scan,
            archivo_id=int(archivo.archivo_id),
            pages=x.pages,
            replace_receta_id=replace_receta_id,
        )
        work.append(w_item)
        headers_render_by_work_id[id(w_item)] = matched_refs_for_archivo
        archivo_ids.append(int(archivo.archivo_id))

    return WorkSelectionOut(
        work=work,
        archivo_ids=archivo_ids,
        revision_items=revision_items,
        headers_render_by_work_id=headers_render_by_work_id,
        revision_reason_by_item_id=revision_reason_by_item_id,
    )


@dataclass(frozen=True)
class PrecomputeOut:
    revision_work: list[_WorkItem]
    estado_render_by_archivo_id: dict[int, dict[str, TroquelEstado]]
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]]
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]]
    revision_reason_by_work_id: dict[int, str]


@dataclass(frozen=True)
class ChunkRuntime:
    tif: TiffProcessor
    storage: S3Storage
    client: MedicamentoClient
    scan_workers: int
    upload_workers: int
    upload_pause_ms: int = 0


def _count_items_with_header(scanned: list[_ScannedItem]) -> int:
    return sum(
        1
        for x in scanned
        if any(norm_str(h) for h in (x.scan.headers or []))
    )


def _is_suspicious_scan(scanned: list[_ScannedItem]) -> bool:
    total = len(scanned)
    if total < 5:
        return False
    with_header = _count_items_with_header(scanned)
    ratio_without_header = 1.0 - (with_header / max(1, total))
    return ratio_without_header >= 0.85


def precompute_render_context(
    *,
    work: list[_WorkItem],
    revision_items: list[_ScannedItem],
    headers_render_by_work_id: dict[int, set[str]],
    archivo_by_id: dict[int, Archivo],
    detalles_by_archivo: dict[int, list[ArchivoDetalle]],
    detalle_ctx_by_archivo: dict[int, _DetalleContext] | None,
    revision_reason_by_item_id: dict[int, str],
    fecha_presentacion_dt: datetime,
    dias_vencimiento: int | None,
    med_cache: dict[str, MedicamentoDTO | None],
    warm_cache: Callable[[set[str]], None],
    resumen: ProcesarResumen,
    stage_cb: ProcessStageCb | None = None,
    vencido_updates: dict[int, bool] | None = None,
) -> PrecomputeOut:
    revision_work: list[_WorkItem] = []
    revision_reason_by_work_id: dict[int, str] = {}
    for x in revision_items:
        w_item = _WorkItem(
            it=x.it,
            scan=x.scan,
            archivo_id=0,
            pages=x.pages,
        )
        revision_work.append(w_item)
        headers_render_by_work_id[id(w_item)] = set()
        revision_reason_by_work_id[id(w_item)] = revision_reason_by_item_id.get(id(x), "Revision")

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

    if stage_cb:
        stage_cb("MED_API START", 0.0)
    med_api_started_at = time.perf_counter()
    warm_cache(all_codebars)
    if stage_cb:
        stage_cb("MED_API", max(0.0, time.perf_counter() - med_api_started_at))

    estado_render_by_archivo_id: dict[int, dict[str, TroquelEstado]] = {}
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]] = {}
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]] = {}

    if stage_cb:
        stage_cb("EVAL_MATCHED START", 0.0)
    eval_matched_started_at = time.perf_counter()

    for w in work:
        archivo = archivo_by_id.get(w.archivo_id)
        if not archivo:
            resumen.errores.append(f"{w.it.file_name}: archivo_id {w.archivo_id} no existe en DB")
            continue

        archivo_ts_value = archivo_ts(archivo)
        esta_vencido_value = esta_vencido(archivo_ts_value, fecha_presentacion_dt, dias_vencimiento)
        if getattr(archivo, "vencido", False) != esta_vencido_value:
            archivo.vencido = esta_vencido_value
            if vencido_updates is not None:
                vencido_updates[int(archivo.archivo_id)] = bool(esta_vencido_value)

        detalle_ctx = None
        if detalle_ctx_by_archivo is not None:
            detalle_ctx = detalle_ctx_by_archivo.get(int(w.archivo_id))

        if detalle_ctx is None:
            dets = detalles_by_archivo.get(w.archivo_id, [])
            detalle_ctx = build_detalle_context(dets)
            if detalle_ctx_by_archivo is not None:
                detalle_ctx_by_archivo[int(w.archivo_id)] = detalle_ctx

        evals = evaluate_troqueles(
            scan_troqueles=(w.scan.troqueles or []),
            detalle=detalle_ctx,
            med_cache=med_cache,
        )

        troquel_evals_by_archivo_id[w.archivo_id] = evals
        troquel_evals_by_work_id[id(w)] = evals
        estado_render_by_archivo_id[w.archivo_id] = to_render_states(evals)

    if stage_cb:
        stage_cb("EVAL_MATCHED", max(0.0, time.perf_counter() - eval_matched_started_at))

    if stage_cb:
        stage_cb("EVAL_REVISION START", 0.0)
    eval_revision_started_at = time.perf_counter()

    for w in revision_work:
        evals = evaluate_revision_troqueles(
            scan_troqueles=(w.scan.troqueles or []),
            med_cache=med_cache,
        )
        troquel_evals_by_work_id[id(w)] = evals

    if stage_cb:
        stage_cb("EVAL_REVISION", max(0.0, time.perf_counter() - eval_revision_started_at))

    return PrecomputeOut(
        revision_work=revision_work,
        estado_render_by_archivo_id=estado_render_by_archivo_id,
        troquel_evals_by_archivo_id=troquel_evals_by_archivo_id,
        troquel_evals_by_work_id=troquel_evals_by_work_id,
        revision_reason_by_work_id=revision_reason_by_work_id,
    )


def process_scanned_batch(
    s: Session,
    *,
    scanned: list[_ScannedItem],
    run_ctx: TifRunContext,
    run_cache: TifRunCache,
    usuario_id: int,
    med_cache: dict[str, MedicamentoDTO | None],
    seen_archivo_ids: set[int],
    asociados_vigentes_iniciales: set[int],
    seen_recetas: set[str],
    seen_refs: set[str],
    revision_counter: int,
    runtime: ChunkRuntime,
    stage_cb: ProcessStageCb | None = None,
) -> ProcesarResumen:
    resumen = ProcesarResumen()

    if not scanned:
        return resumen

    match_started_at = time.perf_counter()
    all_refs: list[str] = []
    for x in scanned:
        all_refs.extend(x.scan.headers or [])

    match = match_all_refs_cached(
        refs=all_refs,
        only_referencia=run_ctx.only_ref_match,
        ref_index=run_cache.ref_index,
        receta_index=run_cache.receta_index,
    )
    if stage_cb:
        stage_cb("MATCH", max(0.0, time.perf_counter() - match_started_at))

    select_started_at = time.perf_counter()

    selection = select_work_items(
        scanned=scanned,
        match=match,
        only_ref_match=run_ctx.only_ref_match,
        archivo_by_id=run_cache.archivo_by_id,
        ref_index=run_cache.ref_index,
        receta_index=run_cache.receta_index,
        receta_vigente_by_archivo_id=run_cache.receta_vigente_by_archivo_id,
        seen_archivo_ids=seen_archivo_ids,
        asociados_vigentes_iniciales=asociados_vigentes_iniciales,
        seen_recetas=seen_recetas,
        seen_refs=seen_refs,
        resumen=resumen,
    )
    if stage_cb:
        stage_cb("SELECT", max(0.0, time.perf_counter() - select_started_at))

    work = selection.work
    archivo_ids = selection.archivo_ids
    revision_items = selection.revision_items
    headers_render_by_work_id = selection.headers_render_by_work_id

    if not work and not revision_items:
        return resumen

    db_bundle_started_at = time.perf_counter()
    archivo_by_id: dict[int, Archivo] = {
        int(archivo_id): archivo
        for archivo_id in archivo_ids
        for archivo in [run_cache.archivo_by_id.get(int(archivo_id))]
        if archivo is not None
    }
    detalles_by_archivo: dict[int, list[ArchivoDetalle]] = {
        int(archivo_id): run_cache.detalles_by_archivo.get(int(archivo_id), [])
        for archivo_id in archivo_ids
        if int(archivo_id) in archivo_by_id
    }
    if stage_cb:
        stage_cb("DB_BUNDLE", max(0.0, time.perf_counter() - db_bundle_started_at))

    precomputed = precompute_render_context(
        work=work,
        revision_items=revision_items,
        headers_render_by_work_id=headers_render_by_work_id,
        archivo_by_id=archivo_by_id,
        detalles_by_archivo=detalles_by_archivo,
        detalle_ctx_by_archivo=run_cache.detalle_ctx_by_archivo,
        revision_reason_by_item_id=selection.revision_reason_by_item_id,
        fecha_presentacion_dt=run_ctx.fecha_presentacion_dt,
        dias_vencimiento=run_ctx.dias_vencimiento,
        med_cache=med_cache,
        warm_cache=lambda codebars: warm_medicamento_cache(runtime.client, med_cache, codebars),
        resumen=resumen,
        stage_cb=stage_cb,
        vencido_updates=run_cache.vencido_updates,
    )

    if stage_cb:
        stage_cb("RENDER+UPLOAD START", 0.0)
    render_upload_started_at = time.perf_counter()
    uploaded, render_elapsed, upload_elapsed = parallel_render_upload(
        storage=runtime.storage,
        tif=runtime.tif,
        work_items=work + precomputed.revision_work,
        archivo_by_id=archivo_by_id,
        prestador_imed=run_ctx.prestador_imed,
        estado_render_by_work=precomputed.estado_render_by_archivo_id,
        headers_render_by_work_id=headers_render_by_work_id,
        upload_workers=runtime.upload_workers,
        upload_pause_ms=runtime.upload_pause_ms,
        resumen=resumen,
    )
    resumen.render_total_seconds += float(render_elapsed or 0.0)
    resumen.upload_total_seconds += float(upload_elapsed or 0.0)
    if stage_cb:
        stage_cb("RENDER", float(render_elapsed or 0.0))
        stage_cb("UPLOAD", float(upload_elapsed or 0.0))
    if stage_cb:
        stage_cb("RENDER+UPLOAD", max(0.0, time.perf_counter() - render_upload_started_at))

    if stage_cb:
        stage_cb("PERSIST START", 0.0)
    persist_started_at = time.perf_counter()
    valid_uploaded = filter_valid_uploaded(uploaded, resumen)
    if not valid_uploaded:
        if stage_cb:
            stage_cb("PERSIST", max(0.0, time.perf_counter() - persist_started_at))
        return resumen

    resumen.ok += persist_uploaded_chunk(
        s,
        recepcion_id=run_ctx.recepcion_id,
        usuario_id=int(usuario_id),
        valid_uploaded=valid_uploaded,
        archivo_by_id=archivo_by_id,
        troquel_evals_by_work_id=precomputed.troquel_evals_by_work_id,
        troquel_evals_by_archivo_id=precomputed.troquel_evals_by_archivo_id,
        revision_reason_by_work_id=precomputed.revision_reason_by_work_id,
        dias_vencimiento=run_ctx.dias_vencimiento,
        motivo_debito_receta_vencida_id=run_ctx.motivo_debito_receta_vencida_id,
        revision_counter=revision_counter,
    )

    run_cache.asociados_vigentes_archivo_ids.update(
        int(u.work.archivo_id)
        for u in valid_uploaded
        if int(u.work.archivo_id) > 0
    )

    if stage_cb:
        stage_cb("PERSIST", max(0.0, time.perf_counter() - persist_started_at))

    del uploaded
    del valid_uploaded
    del precomputed
    del archivo_by_id
    del detalles_by_archivo

    return resumen


def process_chunk(
    s: Session,
    *,
    chunk: list[ProcesarItemIn],
    run_ctx: TifRunContext,
    run_cache: TifRunCache,
    usuario_id: int,
    med_cache: dict[str, MedicamentoDTO | None],
    seen_archivo_ids: set[int],
    asociados_vigentes_iniciales: set[int],
    seen_recetas: set[str],
    seen_refs: set[str],
    revision_counter: int,
    runtime: ChunkRuntime,
) -> ProcesarResumen:
    scan_resumen = ProcesarResumen()
    scanned = parallel_scan(
        tif=runtime.tif,
        items=chunk,
        scan_workers=runtime.scan_workers,
        resumen=scan_resumen,
    )

    retried_safe = False
    if runtime.scan_workers > 1 and _is_suspicious_scan(scanned):
        safe_scan_resumen = ProcesarResumen()
        scanned_safe = parallel_scan(
            tif=runtime.tif,
            items=chunk,
            scan_workers=1,
            resumen=safe_scan_resumen,
        )
        if _count_items_with_header(scanned_safe) > _count_items_with_header(scanned):
            scanned = scanned_safe
            scan_resumen.merge(safe_scan_resumen)
            retried_safe = True

    resumen = process_scanned_batch(
        s,
        scanned=scanned,
        run_ctx=run_ctx,
        run_cache=run_cache,
        usuario_id=usuario_id,
        med_cache=med_cache,
        seen_archivo_ids=seen_archivo_ids,
        asociados_vigentes_iniciales=asociados_vigentes_iniciales,
        seen_recetas=seen_recetas,
        seen_refs=seen_refs,
        revision_counter=revision_counter,
        runtime=runtime,
    )

    resumen.merge(scan_resumen)
    if retried_safe:
        resumen.reintentos_modo_seguro += 1

    del scanned
    return resumen


def _apply_stats(
    total: ProcesarResumen,
    *,
    total_items: int,
    processed_items: int,
    chunk_count: int,
    chunk_elapsed_total: float,
    chunk_min: float,
    chunk_max: float,
    started_at: float,
) -> None:
    elapsed_seconds = max(0.0, time.perf_counter() - started_at)
    items_per_minute = 0.0
    seconds_per_item = 0.0
    if processed_items > 0 and elapsed_seconds > 0:
        items_per_minute = (processed_items / elapsed_seconds) * 60.0
        seconds_per_item = elapsed_seconds / processed_items

    total.stats = ProcesarStats(
        total_items=total_items,
        processed_items=processed_items,
        chunk_count=chunk_count,
        elapsed_seconds=elapsed_seconds,
        items_per_minute=items_per_minute,
        seconds_per_item=seconds_per_item,
        chunk_min_seconds=(chunk_min if chunk_count else 0.0),
        chunk_avg_seconds=((chunk_elapsed_total / chunk_count) if chunk_count else 0.0),
        chunk_max_seconds=chunk_max,
        con_header=total.con_header,
        sin_header=total.sin_header,
        revision_por_sin_match=total.revision_por_sin_match,
        revision_por_ya_asociado=total.revision_por_ya_asociado,
        revision_por_header_vacio=total.revision_por_header_vacio,
        revision_por_header_sin_match=total.revision_por_header_sin_match,
        revision_por_duplicado_lote_ref=total.revision_por_duplicado_lote_ref,
        revision_por_duplicado_lote_receta=total.revision_por_duplicado_lote_receta,
        reintentos_modo_seguro=total.reintentos_modo_seguro,
        render_total_seconds=float(total.render_total_seconds or 0.0),
        upload_total_seconds=float(total.upload_total_seconds or 0.0),
    )


def process_items_in_chunks(
    s: Session,
    *,
    items_filtrados: list[ProcesarItemIn],
    run_ctx: TifRunContext,
    run_cache: TifRunCache,
    usuario_id: int,
    chunk_size: int,
    runtime: ChunkRuntime,
    on_chunk_processed: StageProgressCb | None = None,
    chunk_pause_ms: int = 0,
) -> ProcesarResumen:
    total = ProcesarResumen()
    med_cache: dict[str, MedicamentoDTO | None] = {}
    seen_archivo_ids: set[int] = set()
    asociados_vigentes_iniciales = set(run_cache.asociados_vigentes_archivo_ids)
    seen_recetas: set[str] = set()
    seen_refs: set[str] = set()
    revision_counter = 1
    total_items = len(items_filtrados)
    processed_items = 0
    chunk_count = 0
    chunk_elapsed_total = 0.0
    chunk_min = float("inf")
    chunk_max = 0.0
    started_at = time.perf_counter()

    for chunk in _chunks(items_filtrados, int(chunk_size)):
        chunk_started_at = time.perf_counter()
        resumen = process_chunk(
            s,
            chunk=chunk,
            run_ctx=run_ctx,
            run_cache=run_cache,
            usuario_id=usuario_id,
            med_cache=med_cache,
            seen_archivo_ids=seen_archivo_ids,
            asociados_vigentes_iniciales=asociados_vigentes_iniciales,
            seen_recetas=seen_recetas,
            seen_refs=seen_refs,
            revision_counter=revision_counter,
            runtime=runtime,
        )
        chunk_elapsed = max(0.0, time.perf_counter() - chunk_started_at)

        chunk_count += 1
        chunk_elapsed_total += chunk_elapsed
        chunk_min = min(chunk_min, chunk_elapsed)
        chunk_max = max(chunk_max, chunk_elapsed)

        total.merge(resumen)
        processed_items += len(chunk)
        s.commit()

        if on_chunk_processed:
            on_chunk_processed(processed_items, total_items, chunk_elapsed, "CHUNK")

        pause_ms = max(0, int(chunk_pause_ms))
        if pause_ms > 0 and processed_items < total_items:
            time.sleep(pause_ms / 1000.0)

        s.expunge_all()

        del resumen
        del chunk

    _apply_stats(
        total,
        total_items=total_items,
        processed_items=processed_items,
        chunk_count=chunk_count,
        chunk_elapsed_total=chunk_elapsed_total,
        chunk_min=chunk_min,
        chunk_max=chunk_max,
        started_at=started_at,
    )

    return total


def process_items_individual_async(
    s: Session,
    *,
    items_filtrados: list[ProcesarItemIn],
    run_ctx: TifRunContext,
    run_cache: TifRunCache,
    usuario_id: int,
    runtime: ChunkRuntime,
    on_chunk_processed: StageProgressCb | None = None,
    chunk_pause_ms: int = 0,
) -> ProcesarResumen:
    total = ProcesarResumen()
    med_cache: dict[str, MedicamentoDTO | None] = {}
    seen_archivo_ids: set[int] = set()
    asociados_vigentes_iniciales = set(run_cache.asociados_vigentes_archivo_ids)
    seen_recetas: set[str] = set()
    seen_refs: set[str] = set()
    revision_counter = 1
    total_items = len(items_filtrados)
    processed_items = 0
    chunk_count = 0
    chunk_elapsed_total = 0.0
    chunk_min = float("inf")
    chunk_max = 0.0
    started_at = time.perf_counter()

    if not items_filtrados:
        _apply_stats(
            total,
            total_items=0,
            processed_items=0,
            chunk_count=0,
            chunk_elapsed_total=0.0,
            chunk_min=0.0,
            chunk_max=0.0,
            started_at=started_at,
        )
        return total

    window_size = max(1, int(runtime.scan_workers) * 3)

    with ThreadPoolExecutor(max_workers=max(1, int(runtime.scan_workers))) as ex:
        futures_by_index: dict[int, Future[_ScannedItem]] = {}
        submit_idx = 0

        def _prefetch() -> None:
            nonlocal submit_idx
            while submit_idx < total_items and len(futures_by_index) < window_size:
                it = items_filtrados[submit_idx]
                futures_by_index[submit_idx] = ex.submit(scan_one_item, tif=runtime.tif, it=it)
                submit_idx += 1

        _prefetch()

        for idx in range(total_items):
            item_started_at = time.perf_counter()
            item_number = idx + 1
            stage_totals: dict[str, float] = {}

            def _emit_stage(stage: str, elapsed: float) -> None:
                elapsed_safe = max(0.0, float(elapsed))
                if elapsed_safe > 0:
                    stage_totals[stage] = stage_totals.get(stage, 0.0) + elapsed_safe
                if on_chunk_processed:
                    on_chunk_processed(
                        processed_items,
                        total_items,
                        elapsed_safe,
                        f"[{item_number}/{total_items}] {stage} {elapsed_safe:.2f}s",
                    )

            fut = futures_by_index.pop(idx)

            scan_resumen = ProcesarResumen()
            scanned_items: list[_ScannedItem] = []
            scan_started_at = time.perf_counter()
            try:
                scanned_items = [fut.result()]
            except Exception as e:
                scan_resumen.errores.append(f"scan error: {e}")

            scan_elapsed = max(0.0, time.perf_counter() - scan_started_at)
            if scanned_items:
                scan_data = scanned_items[0].scan
                scan_load = max(0.0, float(getattr(scan_data, "scan_load_seconds", 0.0) or 0.0))
                scan_ocr = max(0.0, float(getattr(scan_data, "scan_ocr_seconds", 0.0) or 0.0))
                scan_zbar = max(0.0, float(getattr(scan_data, "scan_zbar_seconds", 0.0) or 0.0))

                if scan_load > 0:
                    _emit_stage("SCAN_LOAD", scan_load)
                if scan_ocr > 0:
                    _emit_stage("SCAN_OCR", scan_ocr)
                if scan_zbar > 0:
                    _emit_stage("SCAN_ZBAR", scan_zbar)

                residual = scan_elapsed - (scan_load + scan_ocr + scan_zbar)
                if residual > 0.02:
                    _emit_stage("SCAN_OTHER", residual)
            else:
                _emit_stage("SCAN", scan_elapsed)

            resumen_item = process_scanned_batch(
                s,
                scanned=scanned_items,
                run_ctx=run_ctx,
                run_cache=run_cache,
                usuario_id=usuario_id,
                med_cache=med_cache,
                seen_archivo_ids=seen_archivo_ids,
                asociados_vigentes_iniciales=asociados_vigentes_iniciales,
                seen_recetas=seen_recetas,
                seen_refs=seen_refs,
                revision_counter=revision_counter,
                runtime=runtime,
                stage_cb=_emit_stage,
            )
            resumen_item.merge(scan_resumen)

            item_elapsed = max(0.0, time.perf_counter() - item_started_at)
            chunk_count += 1
            chunk_elapsed_total += item_elapsed
            chunk_min = min(chunk_min, item_elapsed)
            chunk_max = max(chunk_max, item_elapsed)

            total.merge(resumen_item)
            processed_items += 1

            _emit_stage("COMMIT START", 0.0)
            commit_started_at = time.perf_counter()
            s.commit()
            _emit_stage("COMMIT", max(0.0, time.perf_counter() - commit_started_at))

            if on_chunk_processed:
                stage_order = [
                    "SCAN_LOAD",
                    "SCAN_OCR",
                    "SCAN_ZBAR",
                    "SCAN_OTHER",
                    "MATCH",
                    "SELECT",
                    "DB_BUNDLE",
                    "MED_API",
                    "EVAL_MATCHED",
                    "EVAL_REVISION",
                    "RENDER",
                    "UPLOAD",
                    "RENDER+UPLOAD",
                    "PERSIST",
                    "COMMIT",
                ]
                detail = " | ".join(
                    f"{name}:{stage_totals[name]:.2f}s"
                    for name in stage_order
                    if stage_totals.get(name, 0.0) > 0
                )
                detail_txt = f" | {detail}" if detail else ""
                on_chunk_processed(
                    processed_items,
                    total_items,
                    item_elapsed,
                    f"[{item_number}/{total_items}] DONE {item_elapsed:.2f}s{detail_txt}",
                )

            pause_ms = max(0, int(chunk_pause_ms))
            if pause_ms > 0 and processed_items < total_items:
                time.sleep(pause_ms / 1000.0)

            s.expunge_all()

            del resumen_item
            del scanned_items
            _prefetch()

    _apply_stats(
        total,
        total_items=total_items,
        processed_items=processed_items,
        chunk_count=chunk_count,
        chunk_elapsed_total=chunk_elapsed_total,
        chunk_min=chunk_min,
        chunk_max=chunk_max,
        started_at=started_at,
    )

    return total
