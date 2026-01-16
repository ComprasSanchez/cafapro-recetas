from datetime import date

from app.db.session import session_scope
from app.db.view import VwArchivoRecetaDebitos


class ViewDebitos:

    @staticmethod
    def list_recepciones() -> list[int]:
        with session_scope() as s:
            rows = (
                s.query(VwArchivoRecetaDebitos.recepcion_id)
                .distinct()
                .order_by(VwArchivoRecetaDebitos.recepcion_id.asc())
                .all()
            )
        return [int(rid) for (rid,) in rows if rid is not None]

    @staticmethod
    def list_debitos(
            recepcion_id: int | None = None,
            fecha_autorizacion: date | None = None,
    ) -> list[VwArchivoRecetaDebitos]:
        """Devuelve filas de vw_archivo_receta_debitos filtradas."""
        with session_scope() as s:
            q = s.query(VwArchivoRecetaDebitos)

            if recepcion_id is not None:
                q = q.filter(VwArchivoRecetaDebitos.recepcion_id == recepcion_id)

            if fecha_autorizacion is not None:
                q = q.filter(VwArchivoRecetaDebitos.fecha == fecha_autorizacion)

            q = q.order_by(
                VwArchivoRecetaDebitos.fecha.asc(),
                VwArchivoRecetaDebitos.hora.asc(),
                VwArchivoRecetaDebitos.orden_lote.asc(),
            )

            return q.all()