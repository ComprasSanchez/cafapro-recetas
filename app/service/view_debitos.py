from datetime import date, datetime, time

from app.db.session import session_scope
from app.db.view import VwArchivoRecetaDebitos

import sqlalchemy as sa


class ViewDebitos:

    @staticmethod
    def list_recepciones() -> list[tuple[int, int]]:
        with session_scope() as s:
            rows = (
                s.query(
                    VwArchivoRecetaDebitos.recepcion_id,
                    VwArchivoRecetaDebitos.recepcion_numero,
                )
                .filter(VwArchivoRecetaDebitos.recepcion_id.isnot(None))
                .distinct()
                .order_by(VwArchivoRecetaDebitos.recepcion_numero.asc())
                .all()
            )

        out: list[tuple[int, int]] = []
        for rid, rnum in rows:
            if rid is None:
                continue
            out.append((int(rid), int(rnum) if rnum is not None else 0))
        return out

    @staticmethod
    def list_debitos(
            recepcion_id: int | None = None,
            fecha_auditoria: date | None = None,
    ) -> list[VwArchivoRecetaDebitos]:
        with session_scope() as s:
            q = s.query(VwArchivoRecetaDebitos)

            if recepcion_id is not None:
                q = q.filter(VwArchivoRecetaDebitos.recepcion_id == int(recepcion_id))

            if fecha_auditoria is not None:
                q = q.filter(sa.cast(VwArchivoRecetaDebitos.creado_en, sa.Date) == fecha_auditoria)

            q = q.order_by(
                VwArchivoRecetaDebitos.fecha.asc(),
                VwArchivoRecetaDebitos.hora.asc(),
                VwArchivoRecetaDebitos.orden_lote.asc(),
            )
            return q.all()