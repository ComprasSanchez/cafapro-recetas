from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
import time
from typing import cast

import httpx

from core.process_tif import ScanOut, TiffProcessor, TroquelEstado
from app.config.settings import settings
from app.service.recetas.tif_context import ArchivoData
from app.service.recetas.tif_logic import (
    base_from_tif_path,
    build_s3_keys,
    norm_str,
    year_month_from_basename_or_fallback,
)
from app.service.recetas.tif_types import ProcesarResumen, _ScannedItem, _UploadResult, _WorkItem


def _upload_rendered(
    *,
    front_key: str | None,
    back_key: str | None,
    front_bytes: bytes | None,
    back_bytes: bytes | None,
) -> None:
    files = {}
    data = {}
    if front_bytes and front_key:
        files["frontFile"] = ("front.jpg", front_bytes, "image/jpeg")
        data["frontKey"] = front_key
    if back_bytes and back_key:
        files["backFile"] = ("back.jpg", back_bytes, "image/jpeg")
        data["backKey"] = back_key
    if not files:
        return
    resp = httpx.post(
        f"{settings.API_CAFAPRO.rstrip('/')}/imagenes/upload",
        files=files,
        data=data,
        timeout=60,
    )
    resp.raise_for_status()


def scan_one_item(*, tif: TiffProcessor, it) -> _ScannedItem:
    try:
        scan, pages = tif.scan_with_pages(it.full_path)
    except Exception:
        scan = tif.scan(it.full_path)
        pages = None

    has_header = any(norm_str(h) for h in (scan.headers or []))
    if not has_header:
        safe_scan = tif.scan(it.full_path)
        if any(norm_str(h) for h in (safe_scan.headers or [])):
            scan = safe_scan
            pages = None

    return _ScannedItem(it=it, scan=scan, pages=pages)


def parallel_scan(
    *,
    tif: TiffProcessor,
    items,
    scan_workers: int,
    resumen: ProcesarResumen,
) -> list[_ScannedItem]:
    out: list[_ScannedItem] = []

    with ThreadPoolExecutor(max_workers=scan_workers) as ex:
        futs = [ex.submit(scan_one_item, tif=tif, it=it) for it in items]
        for fut in as_completed(futs):
            try:
                out.append(fut.result())
            except Exception as e:
                resumen.errores.append(f"scan error: {e}")

    return out


def parallel_render_upload(
    *,
    tif: TiffProcessor,
    work_items: list[_WorkItem],
    archivo_by_id: dict[int, ArchivoData],
    prestador_imed: str,
    estado_render_by_work: dict[int, dict[str, TroquelEstado]],
    headers_render_by_work_id: dict[int, set[str]],
    upload_workers: int,
    upload_pause_ms: int,
    resumen: ProcesarResumen,
) -> tuple[list[_UploadResult], float, float]:
    render_total_seconds = 0.0

    results: list[_UploadResult] = []
    render_total_seconds = 0.0
    upload_total_seconds = 0.0

    def job(w: _WorkItem) -> tuple[_UploadResult, float, float]:
        archivo = archivo_by_id.get(w.archivo_id)
        base_name = base_from_tif_path(w.it.full_path)

        if archivo:
            yyyy, mm = year_month_from_basename_or_fallback(base_name, archivo, w.it.full_path)
        else:
            ts = datetime.fromtimestamp(os.path.getmtime(w.it.full_path))
            yyyy = f"{ts.year:04d}"
            mm = f"{ts.month:02d}"

        front_key, back_key = build_s3_keys(
            prestador_imed=prestador_imed,
            yyyy=yyyy,
            mm=mm,
            base_name=base_name,
        )

        estado = cast(dict[str, TroquelEstado], estado_render_by_work.get(w.archivo_id, {}))
        allowed_headers = {
            norm_str(v)
            for v in headers_render_by_work_id.get(id(w), set())
            if norm_str(v)
        }

        if allowed_headers:
            render_headers = [norm_str(v) for v in (w.scan.headers or []) if norm_str(v) in allowed_headers]
            render_header_dets = [d for d in (w.scan.header_detections or []) if norm_str(d["value"]) in allowed_headers]
        else:
            render_headers, render_header_dets = [], []

        scan_render = ScanOut(
            base_name=w.scan.base_name,
            headers=render_headers,
            troqueles=w.scan.troqueles,
            header_detections=render_header_dets,
            troquel_detections=w.scan.troquel_detections,
        )

        render_started_at = time.perf_counter()
        files = tif.render_bytes(
            tiff_path=w.it.full_path,
            scan=scan_render,
            pages=(w.pages if w.pages else None),
            estado_resolver=lambda codebar: cast(TroquelEstado, estado.get(codebar, "R")),
        )
        fb = files.get("front_bytes")
        bb = files.get("back_bytes")

        if not fb and not bb and w.pages:
            files = tif.render_bytes(
                tiff_path=w.it.full_path,
                scan=scan_render,
                pages=None,
                estado_resolver=lambda codebar: cast(TroquelEstado, estado.get(codebar, "R")),
            )
            fb = files.get("front_bytes")
            bb = files.get("back_bytes")
        render_elapsed = max(0.0, time.perf_counter() - render_started_at)

        upload_started_at = time.perf_counter()
        _upload_rendered(
            front_key=front_key if fb else None,
            back_key=back_key if bb else None,
            front_bytes=fb,
            back_bytes=bb,
        )
        upload_elapsed = max(0.0, time.perf_counter() - upload_started_at)

        pause_ms = max(0, int(upload_pause_ms))
        if pause_ms > 0:
            time.sleep(pause_ms / 1000.0)

        return (
            _UploadResult(work=w, front_key=front_key if fb else None, back_key=back_key if bb else None),
            render_elapsed,
            upload_elapsed,
        )

    workers = max(1, int(upload_workers))
    if workers == 1:
        for w in work_items:
            try:
                out, render_elapsed, upload_elapsed = job(w)
                results.append(out)
                render_total_seconds += render_elapsed
                upload_total_seconds += upload_elapsed
            except Exception as e:
                resumen.errores.append(f"render/upload error: {e}")
        return results, render_total_seconds, upload_total_seconds

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(job, w) for w in work_items]
        for fut in as_completed(futs):
            try:
                out, render_elapsed, upload_elapsed = fut.result()
                results.append(out)
                render_total_seconds += render_elapsed
                upload_total_seconds += upload_elapsed
            except Exception as e:
                resumen.errores.append(f"render/upload error: {e}")

    return results, render_total_seconds, upload_total_seconds
