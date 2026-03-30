from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Callable

from core.process_tif import TroquelEstado
from core.process_tif import TiffProcessor
from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from app.db.models import Archivo, ArchivoDetalle
from app.dto.medicamentos_dto import MedicamentoDTO
from app.infra.s3_storage import S3Storage
from app.service.integraciones.medicamento_client import MedicamentoClient
from app.service.recetas.tif_context import TifRunContext
from app.service.recetas.tif_logic import (
    archivo_ts,
    build_detalle_context,
    esta_vencido,
    evaluate_revision_troqueles,
    evaluate_troqueles,
    match_all_refs,
    norm_str,
    to_render_states,
    warm_medicamento_cache,
)
from app.service.recetas.tif_parallel import parallel_render_upload, parallel_scan, scan_one_item
from app.service.recetas.tif_persistence import filter_valid_uploaded, persist_uploaded_chunk
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
    ProcesarStats,
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

        if refs:
            resumen.con_header += 1
        else:
            resumen.sin_header += 1

        if not refs:
            resumen.sin_match += 1
            resumen.revision_por_sin_match += 1
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
            resumen.revision_por_sin_match += 1
            revision_items.append(x)
            continue

        if is_archivo_ya_asociado(int(archivo.archivo_id)):
            resumen.revision_por_ya_asociado += 1
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

        w_item = _WorkItem(
            it=x.it,
            scan=x.scan,
            archivo_id=int(archivo.archivo_id),
            pages=x.pages,
        )
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
    fecha_presentacion_dt: datetime,
    dias_vencimiento: int | None,
    med_cache: dict[str, MedicamentoDTO | None],
    warm_cache: Callable[[set[str]], None],
    resumen: ProcesarResumen,
    stage_cb: ProcessStageCb | None = None,
) -> PrecomputeOut:
    revision_work: list[_WorkItem] = []
    for x in revision_items:
        w_item = _WorkItem(
            it=x.it,
            scan=x.scan,
            archivo_id=0,
            pages=x.pages,
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

    med_api_started_at = time.perf_counter()
    warm_cache(all_codebars)
    if stage_cb:
        stage_cb("MED_API", max(0.0, time.perf_counter() - med_api_started_at))

    estado_render_by_archivo_id: dict[int, dict[str, TroquelEstado]] = {}
    troquel_evals_by_archivo_id: dict[int, list[_TroquelEval]] = {}
    troquel_evals_by_work_id: dict[int, list[_TroquelEval]] = {}

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

    if stage_cb:
        stage_cb("EVAL_MATCHED", max(0.0, time.perf_counter() - eval_matched_started_at))

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
    )


def process_scanned_batch(
    s: Session,
    *,
    scanned: list[_ScannedItem],
    run_ctx: TifRunContext,
    usuario_id: int,
    med_cache: dict[str, MedicamentoDTO | None],
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

    match = match_all_refs(
        s,
        recepcion_id=run_ctx.recepcion_id,
        refs=all_refs,
        only_referencia=run_ctx.only_ref_match,
    )
    if stage_cb:
        stage_cb("MATCH", max(0.0, time.perf_counter() - match_started_at))

    select_started_at = time.perf_counter()

    selection = select_work_items(
        scanned=scanned,
        match=match,
        only_ref_match=run_ctx.only_ref_match,
        seen_recetas=seen_recetas,
        seen_refs=seen_refs,
        resumen=resumen,
        is_archivo_ya_asociado=lambda archivo_id: TifRepository.is_archivo_ya_asociado(
            s,
            recepcion_id=run_ctx.recepcion_id,
            archivo_id=archivo_id,
        ),
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
    archivo_by_id, detalles_by_archivo = TifRepository.load_archivo_bundle(
        s,
        archivo_ids=archivo_ids,
    )
    if stage_cb:
        stage_cb("DB_BUNDLE", max(0.0, time.perf_counter() - db_bundle_started_at))

    precomputed = precompute_render_context(
        work=work,
        revision_items=revision_items,
        headers_render_by_work_id=headers_render_by_work_id,
        archivo_by_id=archivo_by_id,
        detalles_by_archivo=detalles_by_archivo,
        fecha_presentacion_dt=run_ctx.fecha_presentacion_dt,
        dias_vencimiento=run_ctx.dias_vencimiento,
        med_cache=med_cache,
        warm_cache=lambda codebars: warm_medicamento_cache(runtime.client, med_cache, codebars),
        resumen=resumen,
        stage_cb=stage_cb,
    )

    render_upload_started_at = time.perf_counter()
    uploaded = parallel_render_upload(
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
    if stage_cb:
        stage_cb("RENDER+UPLOAD", max(0.0, time.perf_counter() - render_upload_started_at))

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
        dias_vencimiento=run_ctx.dias_vencimiento,
        motivo_debito_receta_vencida_id=run_ctx.motivo_debito_receta_vencida_id,
        revision_counter=revision_counter,
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
    usuario_id: int,
    med_cache: dict[str, MedicamentoDTO | None],
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
        usuario_id=usuario_id,
        med_cache=med_cache,
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
        reintentos_modo_seguro=total.reintentos_modo_seguro,
    )


def process_items_in_chunks(
    s: Session,
    *,
    items_filtrados: list[ProcesarItemIn],
    run_ctx: TifRunContext,
    usuario_id: int,
    chunk_size: int,
    runtime: ChunkRuntime,
    on_chunk_processed: StageProgressCb | None = None,
    chunk_pause_ms: int = 0,
) -> ProcesarResumen:
    total = ProcesarResumen()
    med_cache: dict[str, MedicamentoDTO | None] = {}
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
            usuario_id=usuario_id,
            med_cache=med_cache,
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
    usuario_id: int,
    runtime: ChunkRuntime,
    on_chunk_processed: StageProgressCb | None = None,
    chunk_pause_ms: int = 0,
) -> ProcesarResumen:
    total = ProcesarResumen()
    med_cache: dict[str, MedicamentoDTO | None] = {}
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
                usuario_id=usuario_id,
                med_cache=med_cache,
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
