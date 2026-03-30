from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
from app.service.recetas.tif_parallel import parallel_render_upload, parallel_scan
from app.service.recetas.tif_persistence import filter_valid_uploaded, persist_uploaded_chunk
from app.service.recetas.tif_types import (
    ProcesarItemIn,
    ProcesarResumen,
    _MatchResult,
    _ScannedItem,
    _TroquelEval,
    _WorkItem,
)


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


@dataclass(frozen=True)
class ChunkRuntime:
    tif: TiffProcessor
    storage: S3Storage
    client: MedicamentoClient
    scan_workers: int
    upload_workers: int


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
    resumen = ProcesarResumen()

    scanned = parallel_scan(
        tif=runtime.tif,
        items=chunk,
        scan_workers=runtime.scan_workers,
        resumen=resumen,
    )
    if not scanned:
        return resumen

    all_refs: list[str] = []
    for x in scanned:
        all_refs.extend(x.scan.headers or [])

    match = match_all_refs(
        s,
        recepcion_id=run_ctx.recepcion_id,
        refs=all_refs,
        only_referencia=run_ctx.only_ref_match,
    )

    candidate_archivo_ids = {
        int(a.archivo_id)
        for a in match.ref_to_archivo.values()
        if a is not None
    }
    archivo_ids_ya_asociados = TifRepository.list_archivo_ids_ya_asociados(
        s,
        recepcion_id=run_ctx.recepcion_id,
        archivo_ids=list(candidate_archivo_ids),
    )

    selection = select_work_items(
        scanned=scanned,
        match=match,
        only_ref_match=run_ctx.only_ref_match,
        seen_recetas=seen_recetas,
        seen_refs=seen_refs,
        resumen=resumen,
        is_archivo_ya_asociado=lambda archivo_id: int(archivo_id) in archivo_ids_ya_asociados,
    )

    work = selection.work
    archivo_ids = selection.archivo_ids
    revision_items = selection.revision_items
    headers_render_by_work_id = selection.headers_render_by_work_id

    if not work and not revision_items:
        return resumen

    archivo_by_id, detalles_by_archivo = TifRepository.load_archivo_bundle(
        s,
        archivo_ids=archivo_ids,
    )

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
    )

    uploaded = parallel_render_upload(
        storage=runtime.storage,
        tif=runtime.tif,
        work_items=work + precomputed.revision_work,
        archivo_by_id=archivo_by_id,
        prestador_imed=run_ctx.prestador_imed,
        estado_render_by_work=precomputed.estado_render_by_archivo_id,
        headers_render_by_work_id=headers_render_by_work_id,
        upload_workers=runtime.upload_workers,
        resumen=resumen,
    )

    valid_uploaded = filter_valid_uploaded(uploaded, resumen)
    if not valid_uploaded:
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

    del uploaded
    del valid_uploaded
    del precomputed
    del archivo_by_id
    del detalles_by_archivo
    del scanned

    return resumen


def process_items_in_chunks(
    s: Session,
    *,
    items_filtrados: list[ProcesarItemIn],
    run_ctx: TifRunContext,
    usuario_id: int,
    chunk_size: int,
    runtime: ChunkRuntime,
    on_chunk_processed: Callable[[int, int], None] | None = None,
) -> ProcesarResumen:
    total = ProcesarResumen()
    med_cache: dict[str, MedicamentoDTO | None] = {}
    seen_recetas: set[str] = set()
    seen_refs: set[str] = set()
    revision_counter = 1
    total_items = len(items_filtrados)
    processed_items = 0

    for chunk in _chunks(items_filtrados, int(chunk_size)):
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
        total.merge(resumen)
        processed_items += len(chunk)

        if on_chunk_processed:
            on_chunk_processed(processed_items, total_items)

        s.expunge_all()

        del resumen
        del chunk

    return total
