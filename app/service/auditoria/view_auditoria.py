from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import select, Row, RowMapping
from sqlalchemy.orm import Session

from app.db.view import VwArchivoResumenAuditoria


class ViewAuditoriaService:
    @staticmethod
    def list(s: Session, recepcion_id: int) -> Sequence[VwArchivoResumenAuditoria]:
        stmt = (
            select(VwArchivoResumenAuditoria)
            .where(VwArchivoResumenAuditoria.recepcion_id == recepcion_id)
            .order_by(VwArchivoResumenAuditoria.frente_jpg.asc())
        )
        return s.execute(stmt).scalars().all()

    @staticmethod
    def list_sin_asociacion(
            s: Session,
            recepcion_id: int,
    ):
        rows = s.execute(
            select(VwArchivoResumenAuditoria)
            .where(
                VwArchivoResumenAuditoria.recepcion_id == recepcion_id,
                VwArchivoResumenAuditoria.existe_archivo.is_(True),
                VwArchivoResumenAuditoria.asociacion_id.is_(None),
            )
            .order_by(VwArchivoResumenAuditoria.numero_referencia)
        ).scalars().all()

        return rows

    @staticmethod
    def list_archivos_reasociables(
            s: Session,
            recepcion_id: int,
    ):
        rows = s.execute(
            select(VwArchivoResumenAuditoria)
            .where(
                VwArchivoResumenAuditoria.recepcion_id == recepcion_id,
                VwArchivoResumenAuditoria.asociacion_id.is_not(None),
                VwArchivoResumenAuditoria.estado_receta_id == 1,
            )
            .order_by(VwArchivoResumenAuditoria.numero_referencia)
        ).scalars().all()

        return rows

