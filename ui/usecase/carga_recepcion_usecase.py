from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db.session import session_scope
from app.service.recepcion.recepcion_service import RecepcionService
from app.service.recetas.tif_service import ProcesarItemIn, TiffService
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
class ProcesarOut:
    resumen: Any

@dataclass(frozen=True)
class CloseRecepcionOut:
    recepcion_id: int
    estado_recepcion_id: int


class CargaRecepcionUseCase:

    @staticmethod
    def load_recepcion(*, recepcion_id: int, ctx=None) -> LoadRecepcionOut:
        if ctx:
            ctx.emit_progress(10, "Leyendo recepción…")

        with session_scope() as s:
            svc = RecepcionService()
            rows = svc.list(s)

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            raise ValueError("No se encontró la recepción seleccionada.")

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
            ctx.emit_progress(10, "Buscando imágenes…")

        img = ImageHandler(parent=None)  # ideal: que ImageHandler no dependa de Qt
        rows = img.get_images_tif(name_folder=imed, date=date_str, obs=obs)

        if ctx:
            ctx.emit_progress(90, f"Encontradas {len(rows)} imágenes")

        return ListImagesOut(rows=rows)

    @staticmethod
    def procesar(*, recepcion_id: int, usuario_id: int, items: list[ProcesarItemIn], output_dir: str, ctx=None) -> ProcesarOut:
        if ctx:
            ctx.emit_progress(5, "Procesando TIFFs…")

        with session_scope() as s:
            svc = TiffService()
            resumen = svc.procesar(
                s=s,
                recepcion_id=recepcion_id,
                usuario_id=usuario_id,
                items=items,
                output_dir=output_dir,
            )

        if ctx:
            ctx.emit_progress(100, "Procesamiento finalizado")

        return ProcesarOut(resumen=resumen)

    @staticmethod
    def cerrar_recepcion(recepcion_id: int) -> CloseRecepcionOut:
        with session_scope() as s:
            RecepcionService.cerrar_recepcion(s, recepcion_id=recepcion_id)
            return CloseRecepcionOut(recepcion_id=recepcion_id, estado_recepcion_id=2)

