# app/use_cases/auditoria_usecase.py
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.config.settings import settings
from app.db.session import session_scope
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.asociacion_service import AsociacionService
from app.service.recetas.estado_receta_service import EstadoRecetaService
from app.service.auditoria.view_auditoria import ViewAuditoriaService
import requests
from urllib.parse import quote


@dataclass(frozen=True)
class RecepcionOut:
    recepcion_id: int
    numero: str
    prestador: str
    obra_social: str
    periodo: str


@dataclass(frozen=True)
class EstadosOut:
    estados: list[tuple[int, str]]  # [(id, descripcion), ...]


@dataclass(frozen=True)
class AuditoriaRowsOut:
    rows: list  # rows de la view (SQLAlchemy row / namedtuple)
    search_cache: list[tuple[str, str, str]]  # lower() receta/ref/lote


@dataclass(frozen=True)
class PreviewBytesOut:
    path: str
    img_bytes: bytes  # PNG bytes
    w: int
    h: int


class AuditoriaUseCase:

    @staticmethod
    def resolve_preview_src(raw: str) -> str:
        """
        raw puede ser:
          - key S3 (imed/2026/02/xxx_f.jpg)
          - URL completa (https://...)
          - path local (C:\\... o /...)
        Devuelve:
          - URL (si era key) o
          - el mismo valor (si ya era URL o path)
        """
        raw = (raw or "").strip()
        if not raw:
            return ""

        low = raw.lower()

        # ya es URL
        if low.startswith("http://") or low.startswith("https://"):
            return raw

        # path local (Windows UNC / drive / Linux)
        if (len(raw) >= 3 and raw[1:3] == ":\\") or raw.startswith("\\\\") or raw.startswith("/"):
            return raw

        # si no, asumimos KEY S3
        base = (getattr(settings, "CLOUDFRONT_BASE_URL", "") or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            # sin base no podemos armar URL (te va a fallar más claro luego)
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
        # Windows: C:\... o \\server\share
        if len(x) >= 3 and x[1:3] == ":\\":
            return True
        if x.startswith("\\\\"):
            return True
        # Linux/mac path
        if x.startswith("/"):
            return True
        return False

    @staticmethod
    def _to_cloudfront_url(key_or_url_or_path: str) -> str:
        v = (key_or_url_or_path or "").strip()
        if not v:
            return ""

        # si ya es URL, no tocar
        if AuditoriaUseCase._is_url(v):
            return v

        # si parece path local, no tocar (compat)
        if AuditoriaUseCase._looks_like_local_path(v):
            return v

        # si no, asumimos KEY
        base = (settings.CLOUDFRONT_BASE_URL or "").strip()
        base = base.replace("https://", "").replace("http://", "").strip().rstrip("/")
        if not base:
            # si no hay base, devolvemos el key tal cual (y va a fallar más claro)
            return v

        key = quote(v.lstrip("/"), safe="/")
        return f"https://{base}/{key}"

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> RecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepción…")

        with session_scope() as s:
            rows = RecepcionService.list(s)

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            raise ValueError("No se encontró la recepción seleccionada.")

        if ctx:
            ctx.emit_progress(90, "Recepción lista")

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
            ctx.emit_progress(10, "Cargando estados…")

        with session_scope() as s:
            estados = EstadoRecetaService.list(s)

        out = [(int(e.estado_receta_id), str(e.descripcion)) for e in (estados or [])]

        if ctx:
            ctx.emit_progress(100, "Estados listos")

        return EstadosOut(estados=out)

    @staticmethod
    def load_auditoria(*, recepcion_id: int, ctx=None) -> AuditoriaRowsOut:
        if ctx:
            ctx.emit_progress(10, "Cargando auditoría…")

        with session_scope() as s:
            rows = list(ViewAuditoriaService.list(s, recepcion_id))

        if ctx:
            ctx.emit_progress(70, "Preparando búsqueda…")

        search_cache = [
            (
                str(getattr(r, "numero_receta", "") or "").lower(),
                str(getattr(r, "numero_referencia", "") or "").lower(),
                str(getattr(r, "nro_lote", "") or "").lower(),
            )
            for r in rows
        ]

        if ctx:
            ctx.emit_progress(100, f"Auditoría lista ({len(rows)})")

        return AuditoriaRowsOut(rows=rows, search_cache=search_cache)

    @staticmethod
    def load_preview_bytes(*, path: str, vw: int, vh: int, ctx=None) -> PreviewBytesOut:
        raw = (path or "").strip()
        if not raw:
            raise ValueError("Path/key vacío")

        if ctx:
            ctx.emit_progress(10, "Cargando imagen…")

        # 1) resolver a "fuente" (local path o URL)
        src = AuditoriaUseCase._to_cloudfront_url(raw)

        # 2) obtener bytes
        if AuditoriaUseCase._is_url(src):
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
            ctx.emit_progress(40, "Decodificando…")

        # 3) PIL desde bytes
        pil_img = Image.open(io.BytesIO(data)).convert("RGB")

        vw = max(200, int(vw))
        vh = max(200, int(vh))

        scale = min(vw / pil_img.width, vh / pil_img.height)
        scale = max(scale, 0.30)

        new_w = int(pil_img.width * scale)
        new_h = int(pil_img.height * scale)

        if ctx:
            ctx.emit_progress(70, "Escalando…")

        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        if ctx:
            ctx.emit_progress(100, "Imagen lista")

        # devolvemos "src" para comparar en UI (si cambió la selección)
        return PreviewBytesOut(path=src, img_bytes=img_bytes, w=new_w, h=new_h)

    @staticmethod
    def load_archivos(recepcion_id: int):

        with session_scope() as s:
            return ViewAuditoriaService.list_sin_asociacion(
                s,
                recepcion_id,
            )

    @staticmethod
    def ejecutar(
            receta_id: int,
            archivo_id: int,
    ):

        with session_scope() as s:
            AsociacionService.ejecutar(
                s,
                receta_id=receta_id,
                archivo_id=archivo_id,
            )




