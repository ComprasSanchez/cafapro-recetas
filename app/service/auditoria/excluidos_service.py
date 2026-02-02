from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.view import VwArchivosExcluidos


class ExcluidosService:
    @staticmethod
    def list_by_recepcion(session: Session, recepcion_id: int) -> list[VwArchivosExcluidos]:
        stmt = (
            select(VwArchivosExcluidos)
            .where(VwArchivosExcluidos.recepcion_id == int(recepcion_id))
            .order_by(
                VwArchivosExcluidos.nro_referencia.asc(),
                VwArchivosExcluidos.nro_receta.asc(),
            )
        )
        return list(session.execute(stmt).scalars().all())
