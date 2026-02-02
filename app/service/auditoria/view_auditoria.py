from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.view import VwArchivoResumenAuditoria


class ViewAuditoriaService:
    @staticmethod
    def list(s: Session, recepcion_id: int) -> list[VwArchivoResumenAuditoria]:
        stmt = (
            select(VwArchivoResumenAuditoria)
            .where(VwArchivoResumenAuditoria.recepcion_id == recepcion_id)
        )
        return s.execute(stmt).scalars().all()

