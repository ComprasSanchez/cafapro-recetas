# app/use_cases/auditoria_usecase.py
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.db.session import session_scope
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.estado_receta_service import EstadoRecetaService
from app.service.auditoria.view_auditoria import ViewAuditoriaService


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
        """
        Lee la imagen con PIL en background, la escala y la devuelve como PNG bytes.
        UI luego arma QPixmap.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"No existe: {p}")

        if ctx:
            ctx.emit_progress(10, "Cargando imagen…")

        pil_img = Image.open(p).convert("RGB")

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

        return PreviewBytesOut(path=str(p), img_bytes=img_bytes, w=new_w, h=new_h)
