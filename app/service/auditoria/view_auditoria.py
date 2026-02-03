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

