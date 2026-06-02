from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

from app.config.settings import settings
from app.service.auditoria.view_auditoria import ViewAuditoriaService
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.asociacion_service import AsociacionService
from app.service.recetas.estado_receta_service import EstadoRecetaService
from app.service.recetas.historial_receta_service import HistorialRecetaService
from app.service.recetas.recetas_service import RecetaService


@dataclass(frozen=True)
class RecepcionOut:
    recepcion_id: int
    numero: str
    prestador: str
    obra_social: str
    periodo: str


@dataclass(frozen=True)
class EstadosOut:
    estados: list[tuple[int, str]]


@dataclass(frozen=True)
class AuditoriaRowsOut:
    rows: list
    search_cache: list[tuple[str, str, str]]


@dataclass(frozen=True)
class PreviewBytesOut:
    path: str
    img_bytes: bytes
    w: int
    h: int


class AuditoriaApplication:
    @staticmethod
    def resolve_preview_src(raw: str) -> str:
        raw = (raw or "").strip()
        if not raw:
            return ""

        low = raw.lower()
        if low.startswith("http://") or low.startswith("https://"):
            return raw

        if (len(raw) >= 3 and raw[1:3] == ":\\") or raw.startswith("\\\\") or raw.startswith("/"):
            return raw

        base = (getattr(settings, "CLOUDFRONT_BASE_URL", "") or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            return raw

        key = quote(raw.lstrip("/"), safe="/")
        return f"https://{base}/{key}"

    @staticmethod
    def _is_url(x: str) -> bool:
        x = (x or "").strip().lower()
        return x.startswith("http://") or x.startswith("https://")

    @staticmethod
    def _looks_like_local_path(x: str) -> bool:
        x = (x or "").strip()
        if not x:
            return False
        if len(x) >= 3 and x[1:3] == ":\\":
            return True
        if x.startswith("\\\\"):
            return True
        if x.startswith("/"):
            return True
        return False

    @staticmethod
    def _to_cloudfront_url(key_or_url_or_path: str) -> str:
        v = (key_or_url_or_path or "").strip()
        if not v:
            return ""

        if AuditoriaApplication._is_url(v):
            return v

        if AuditoriaApplication._looks_like_local_path(v):
            return v

        base = (settings.CLOUDFRONT_BASE_URL or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            return v

        key = quote(v.lstrip("/"), safe="/")
        return f"https://{base}/{key}"

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> RecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepcion...")

        rec = RecepcionService.get(recepcion_id)
        if not rec:
            raise ValueError("No se encontro la recepcion seleccionada.")

        if ctx:
            ctx.emit_progress(90, "Recepcion lista")

        return RecepcionOut(
            recepcion_id=rec.recepcion_id,
            numero=str(getattr(rec, "numero", "") or ""),
            prestador=str(getattr(rec, "prestador", "") or ""),
            obra_social=str(getattr(rec, "obra_social", "") or ""),
            periodo=str(getattr(rec, "periodo", "") or ""),
        )

    @staticmethod
    def load_estados(*, ctx=None) -> EstadosOut:
        if ctx:
            ctx.emit_progress(10, "Cargando estados...")

        estados = EstadoRecetaService.list()
        out = [(int(e.estado_receta_id), str(e.descripcion)) for e in (estados or [])]

        if ctx:
            ctx.emit_progress(100, "Estados listos")

        return EstadosOut(estados=out)

    @staticmethod
    def load_auditoria(*, recepcion_id: int, ctx=None) -> AuditoriaRowsOut:
        if ctx:
            ctx.emit_progress(10, "Cargando auditoria...")

        rows = list(ViewAuditoriaService.list(recepcion_id))

        if ctx:
            ctx.emit_progress(70, "Preparando busqueda...")

        search_cache = [
            (
                str(getattr(r, "numero_receta", "") or "").lower(),
                str(getattr(r, "numero_referencia", "") or "").lower(),
                str(getattr(r, "nro_lote", "") or "").lower(),
            )
            for r in rows
        ]

        if ctx:
            ctx.emit_progress(100, f"Auditoria lista ({len(rows)})")

        return AuditoriaRowsOut(rows=rows, search_cache=search_cache)

    @staticmethod
    def load_preview_bytes(*, path: str, vw: int, vh: int, ctx=None) -> PreviewBytesOut:
        raw = (path or "").strip()
        if not raw:
            raise ValueError("Path/key vacio")

        if ctx:
            ctx.emit_progress(10, "Cargando imagen...")

        src = AuditoriaApplication._to_cloudfront_url(raw)

        if AuditoriaApplication._is_url(src):
            try:
                r = requests.get(src, timeout=20)
                r.raise_for_status()
                data = r.content
            except Exception as e:
                raise RuntimeError(f"No se pudo descargar la imagen desde CloudFront: {e}")
        else:
            p = Path(src)
            if not p.exists():
                raise FileNotFoundError(f"No existe: {p}")
            data = p.read_bytes()

        if ctx:
            ctx.emit_progress(40, "Decodificando...")

        pil_img = Image.open(io.BytesIO(data)).convert("RGB")

        vw = max(200, int(vw))
        vh = max(200, int(vh))

        scale = min(vw / pil_img.width, vh / pil_img.height)
        scale = max(scale, 0.30)

        new_w = int(pil_img.width * scale)
        new_h = int(pil_img.height * scale)

        if ctx:
            ctx.emit_progress(70, "Escalando...")

        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        if ctx:
            ctx.emit_progress(100, "Imagen lista")

        return PreviewBytesOut(path=src, img_bytes=img_bytes, w=new_w, h=new_h)

    @staticmethod
    def load_archivos(recepcion_id: int):
        return ViewAuditoriaService.list_sin_asociacion(recepcion_id)

    @staticmethod
    def ejecutar(*, receta_id: int, archivo_id: int):
        AsociacionService.ejecutar(receta_id=receta_id, archivo_id=archivo_id)

    @staticmethod
    def load_archivos_reasociables(recepcion_id: int):
        return ViewAuditoriaService.list_archivos_reasociables(recepcion_id)

    @staticmethod
    def reasociar(*, receta_id: int, archivo_id: int):
        AsociacionService.reasociar(receta_id=receta_id, archivo_id=archivo_id)

    @staticmethod
    def anular_receta(*, receta_id: int, nro_receta: str) -> None:
        RecetaService.anular_receta(receta_id=receta_id, nro_receta=nro_receta)

    @staticmethod
    def duplicar_receta(*, receta_id: int, nro_receta: str) -> None:
        RecetaService.duplicar_receta(receta_id=receta_id, nro_receta=nro_receta)

    @staticmethod
    def eliminar_sobrante(*, receta_id: int) -> None:
        RecetaService.eliminar_sobrante(receta_id=receta_id)

    @staticmethod
    def eliminar_sobrantes_bulk(*, receta_ids: list[int]) -> dict:
        return RecetaService.eliminar_sobrantes_bulk(receta_ids=list(receta_ids or []))

    @staticmethod
    def desasociar_receta(*, receta_id: int) -> None:
        AsociacionService.desasociar(receta_id=receta_id)

    @staticmethod
    def load_historial_snapshot(*, archivo_id: int):
        return HistorialRecetaService.load_current_snapshot(archivo_id=archivo_id)

    @staticmethod
    def load_historial_rows(*, archivo_id: int) -> list[dict]:
        return HistorialRecetaService.list_historial(archivo_id=archivo_id)

    @staticmethod
    def load_historial_detail(*, receta_id: int) -> tuple[list[dict], dict]:
        debs = HistorialRecetaService.list_debitos_for_receta(receta_id=receta_id)
        imgs = HistorialRecetaService.get_imagenes_por_receta(receta_id=receta_id)
        return debs, imgs

    @staticmethod
    def search_historial_by_numero_receta(*, nro_receta: str) -> list[dict]:
        value = str(nro_receta or "").strip()
        if not value:
            raise ValueError("Debés ingresar un número de receta.")
        return HistorialRecetaService.search_historial_by_numero_receta(nro_receta=value)

    @staticmethod
    def search_historial_by_numero_referencia(*, nro_referencia: str) -> list[dict]:
        value = str(nro_referencia or "").strip()
        if not value:
            raise ValueError("Debés ingresar un número de referencia.")
        return HistorialRecetaService.search_historial_by_numero_referencia(nro_referencia=value)
