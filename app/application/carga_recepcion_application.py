from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Any

from core.api_client import get_client, TIMEOUT_HEAVY

from app.config.settings import settings
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.archivo_service import ArchivoService
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
    _STAGE_LABELS: dict[str, str] = {
        "SCAN_LOAD": "Cargando páginas TIFF",
        "SCAN_OCR": "Leyendo encabezado (OCR)",
        "SCAN_ZBAR": "Leyendo códigos de barra",
        "SCAN_OTHER": "Preparando lectura",
        "MATCH": "Buscando coincidencia",
        "SELECT": "Validando receta",
        "DB_BUNDLE": "Leyendo datos del archivo",
        "MED_API": "Consultando medicamentos",
        "EVAL_MATCHED": "Evaluando troqueles asociados",
        "EVAL_REVISION": "Evaluando troqueles en revisión",
        "RENDER": "Renderizando imágenes",
        "UPLOAD": "Subiendo imágenes",
        "RENDER+UPLOAD": "Generando y subiendo imágenes",
        "PERSIST": "Guardando resultados",
        "COMMIT": "Confirmando cambios",
        "DONE": "Completado",
    }

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        hh, rem = divmod(total, 3600)
        mm, ss = divmod(rem, 60)
        if hh > 0:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        return f"{mm:02d}:{ss:02d}"

    @staticmethod
    def _humanize_stage(stage: str) -> str:
        raw = str(stage or "").strip()
        if not raw:
            return "Procesando"

        item_prefix = ""
        body = raw
        m = re.match(r"^\[(\d+/\d+)\]\s+(.+)$", raw)
        if m:
            item_prefix = f"[{m.group(1)}] "
            body = m.group(2)

        ordered_labels = sorted(
            CargaRecepcionApplication._STAGE_LABELS.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        for code, label in ordered_labels:
            body = body.replace(code, label)

        body = body.replace(" START", " (iniciando)")
        return f"{item_prefix}{body}"

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> LoadRecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepcion...")

        rec = RecepcionService.get(recepcion_id)
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

        svc = TiffService(
            chunk_size=int(settings.TIFF_CHUNK_SIZE),
            scan_workers=int(settings.TIFF_SCAN_WORKERS),
            upload_workers=int(settings.TIFF_UPLOAD_WORKERS),
            chunk_pause_ms=int(settings.TIFF_CHUNK_PAUSE_MS),
            upload_pause_ms=int(settings.TIFF_UPLOAD_PAUSE_MS),
            pipeline_mode=str(getattr(settings, "TIFF_PIPELINE_MODE", "item") or "item"),
        )

        total_items = len(input_items)

        def _emit_chunk_progress(done: int, total: int, chunk_elapsed: float, stage: str) -> None:
            elapsed = max(0.001, time.perf_counter() - started_at)
            total_safe = max(1, int(total))
            done_safe = max(0, min(int(done), total_safe))
            percent = 15 + int((done_safe / total_safe) * 80)
            stage_text = CargaRecepcionApplication._humanize_stage(stage)
            eta_text = "--:--"
            if done_safe > 0 and done_safe < total_safe:
                remaining = total_safe - done_safe
                eta_seconds = (remaining / done_safe) * elapsed
                eta_text = CargaRecepcionApplication._fmt_duration(eta_seconds)

            msg = (
                f"{stage_text}"
                f" | {done_safe}/{total_safe} recetas"
                f" | ETA {eta_text}"
            )

            if ctx:
                ctx.emit_progress(percent, msg)

        resumen = svc.procesar(
            recepcion_id=recepcion_id,
            usuario_id=usuario_id,
            items=input_items,
            progress_cb=_emit_chunk_progress if total_items else None,
        )

        resp = get_client().post(
            f"{settings.API_CAFAPRO.rstrip('/')}/recepciones/{recepcion_id}/actualizar-historial",
            timeout=TIMEOUT_HEAVY,
        )
        resp.raise_for_status()

        total_elapsed = max(0.0, time.perf_counter() - started_at)

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
        RecepcionService.cerrar_recepcion(recepcion_id)
        return CloseRecepcionOut(recepcion_id=recepcion_id, estado_recepcion_id=2)

    @staticmethod
    def list_fechas_descargadas(*, recepcion_id: int):
        return ArchivoService.list_fechas(recepcion_id)
