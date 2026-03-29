from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.adapters.sqlalchemy.tif_repository import TifRepository
from app.service.recetas.tif_logic import base_from_tif_path, is_valesalud
from app.service.recetas.tif_types import ProcesarItemIn


MOTIVO_DEBITO_RECETA_VENCIDA_ID = 11


@dataclass(frozen=True)
class TifRunContext:
    recepcion_id: int
    prestador_imed: str
    fecha_presentacion_dt: datetime
    dias_vencimiento: int | None
    only_ref_match: bool
    motivo_debito_receta_vencida_id: int = MOTIVO_DEBITO_RECETA_VENCIDA_ID


def load_run_context(session: Session, *, recepcion_id: int) -> TifRunContext:
    rec = TifRepository.get_recepcion(session, recepcion_id=int(recepcion_id))
    if not rec:
        raise RuntimeError(f"No existe la recepcion {recepcion_id}")

    pr_row = TifRepository.get_prestador(session, prestador_id=int(rec.prestador_id))
    if not pr_row:
        raise RuntimeError("No existe el prestador asociado a la recepcion.")

    prestador_imed = (getattr(pr_row, "imed", "") or "").strip()
    if not prestador_imed:
        raise RuntimeError("Prestador.imed esta vacio; no se puede armar key S3.")

    fecha_presentacion = rec.fecha_presentacion
    if isinstance(fecha_presentacion, datetime):
        fecha_presentacion_dt = fecha_presentacion
    else:
        fecha_presentacion_dt = datetime.fromisoformat(str(fecha_presentacion))

    os_row = TifRepository.get_obra_social_context(session, obra_social_id=int(rec.obra_social_id))
    os_nombre = os_row[0] if os_row else None
    dias_vencimiento_raw = os_row[1] if os_row else None
    dias_vencimiento = int(dias_vencimiento_raw) if dias_vencimiento_raw is not None else None

    return TifRunContext(
        recepcion_id=int(recepcion_id),
        prestador_imed=prestador_imed,
        fecha_presentacion_dt=fecha_presentacion_dt,
        dias_vencimiento=dias_vencimiento,
        only_ref_match=is_valesalud(os_nombre),
    )


def filter_unprocessed_items(
    session: Session,
    *,
    recepcion_id: int,
    items: list[ProcesarItemIn],
) -> tuple[list[ProcesarItemIn], int]:
    items_filtrados: list[ProcesarItemIn] = []
    ya_asociado = 0

    for it in items:
        base_name = base_from_tif_path(it.full_path)
        if base_name and TifRepository.exists_processed_base_in_recepcion(
            session,
            recepcion_id=int(recepcion_id),
            base_name=base_name,
        ):
            ya_asociado += 1
            continue
        items_filtrados.append(it)

    return items_filtrados, ya_asociado
