from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any

from app.config.settings import settings
from app.db.session import session_scope
from app.infra.storage import s3_storage
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.archivo_service import ArchivoService
from app.service.recetas.historial_receta_service import HistorialRecetaService
from app.service.recetas.tif_service import ProcesarItemIn as TiffProcesarItemIn, TiffService
from core.image_handler import ImageHandler


@dataclass(frozen=True)
class LoadRecepcionOut:
    recepcion_id: int
    numero: str
    prestador: str
    obra_social: str
    periodo: str
    imed: str
    obs: str


@dataclass(frozen=True)
class ListImagesOut:
    rows: list[dict]


@dataclass(frozen=True)
class ProcesarCargaIn:
    file_name: str
    full_path: str


@dataclass(frozen=True)
class ProcesarOut:
    resumen: Any


@dataclass(frozen=True)
class CloseRecepcionOut:
    recepcion_id: int
    estado_recepcion_id: int


class CargaRecepcionApplication:
    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        hh, rem = divmod(total, 3600)
        mm, ss = divmod(rem, 60)
        if hh > 0:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        return f"{mm:02d}:{ss:02d}"

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> LoadRecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepcion...")

        with session_scope() as s:
            svc = RecepcionService()
            rows = svc.list(s)

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            raise ValueError("No se encontro la recepcion seleccionada.")

        return LoadRecepcionOut(
            recepcion_id=rec.recepcion_id,
            numero=str(getattr(rec, "numero", "") or ""),
            prestador=str(getattr(rec, "prestador", "") or ""),
            obra_social=str(getattr(rec, "obra_social", "") or ""),
            periodo=str(getattr(rec, "periodo", "") or ""),
            imed=str(getattr(rec, "imed", "") or ""),
            obs=str(getattr(rec, "obra_social", "") or ""),
        )

    @staticmethod
    def list_images(*, imed: str, obs: str, date_str: str, ctx=None) -> ListImagesOut:
        if ctx:
            ctx.emit_progress(10, "Buscando imagenes...")

        img = ImageHandler(parent=None)
        rows = img.get_images_tif(name_folder=imed, date=date_str, obs=obs)

        if ctx:
            ctx.emit_progress(90, f"Encontradas {len(rows)} imagenes")

        return ListImagesOut(rows=rows)

    @staticmethod
    def procesar(*, recepcion_id: int, usuario_id: int, items: list[ProcesarCargaIn], ctx=None) -> ProcesarOut:
        if ctx:
            ctx.emit_progress(5, "Procesando TIFFs...")

        started_at = time.perf_counter()

        input_items = [
            TiffProcesarItemIn(file_name=x.file_name, full_path=x.full_path)
            for x in (items or [])
        ]

        with session_scope() as s:
            svc = TiffService(
                storage=s3_storage,
                chunk_size=int(settings.TIFF_CHUNK_SIZE),
                scan_workers=int(settings.TIFF_SCAN_WORKERS),
                upload_workers=int(settings.TIFF_UPLOAD_WORKERS),
                chunk_pause_ms=int(settings.TIFF_CHUNK_PAUSE_MS),
                upload_pause_ms=int(settings.TIFF_UPLOAD_PAUSE_MS),
            )

            total_items = len(input_items)
            checkpoint_dir = Path("output") / "process_checkpoints"
            checkpoint_path = checkpoint_dir / f"recepcion_{int(recepcion_id)}.json"

            def _write_checkpoint(payload: dict[str, Any]) -> None:
                try:
                    checkpoint_dir.mkdir(parents=True, exist_ok=True)
                    checkpoint_path.write_text(
                        json.dumps(payload, ensure_ascii=True, indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    pass

            def _emit_chunk_progress(done: int, total: int, chunk_elapsed: float) -> None:
                elapsed = max(0.001, time.perf_counter() - started_at)
                total_safe = max(1, int(total))
                done_safe = max(0, min(int(done), total_safe))
                percent = 15 + int((done_safe / total_safe) * 80)
                items_per_minute = (done_safe / elapsed) * 60.0 if done_safe > 0 else 0.0
                eta_text = "--:--"
                if done_safe > 0 and done_safe < total_safe:
                    remaining = total_safe - done_safe
                    eta_seconds = (remaining / done_safe) * elapsed
                    eta_text = CargaRecepcionApplication._fmt_duration(eta_seconds)

                msg = (
                    f"Procesando TIFFs... {done_safe}/{total_safe}"
                    f" | {items_per_minute:.1f} rec/min"
                    f" | ETA {eta_text}"
                    f" | chunk {chunk_elapsed:.1f}s"
                )

                _write_checkpoint(
                    {
                        "recepcion_id": int(recepcion_id),
                        "done": done_safe,
                        "total": total_safe,
                        "percent": percent,
                        "elapsed_seconds": elapsed,
                        "items_per_minute": items_per_minute,
                        "chunk_elapsed_seconds": float(chunk_elapsed),
                        "eta": eta_text,
                        "status": "running",
                    }
                )

                if ctx:
                    ctx.emit_progress(percent, msg)

            resumen = svc.procesar(
                s=s,
                recepcion_id=recepcion_id,
                usuario_id=usuario_id,
                items=input_items,
                progress_cb=_emit_chunk_progress if total_items else None,
            )

            s.flush()

            HistorialRecetaService.actualizar_historial_recepcion(
                s=s,
                recepcion_id=recepcion_id,
            )

        total_elapsed = max(0.0, time.perf_counter() - started_at)
        final_stats = getattr(resumen, "stats", None)
        _write_checkpoint(
            {
                "recepcion_id": int(recepcion_id),
                "done": int(getattr(final_stats, "processed_items", len(input_items)) or 0),
                "total": len(input_items),
                "elapsed_seconds": total_elapsed,
                "items_per_minute": float(getattr(final_stats, "items_per_minute", 0.0) or 0.0),
                "seconds_per_item": float(getattr(final_stats, "seconds_per_item", 0.0) or 0.0),
                "status": "finished",
            }
        )

        if ctx:
            ctx.emit_progress(
                100,
                (
                    "Procesamiento finalizado"
                    f" | tiempo {CargaRecepcionApplication._fmt_duration(total_elapsed)}"
                ),
            )

        return ProcesarOut(resumen=resumen)

    @staticmethod
    def cerrar_recepcion(recepcion_id: int) -> CloseRecepcionOut:
        with session_scope() as s:
            RecepcionService.cerrar_recepcion(s, recepcion_id=recepcion_id)
            return CloseRecepcionOut(recepcion_id=recepcion_id, estado_recepcion_id=2)

    @staticmethod
    def list_fechas_descargadas(*, recepcion_id: int):
        with session_scope() as s:
            return ArchivoService.list_fechas(s, recepcion_id=recepcion_id)
