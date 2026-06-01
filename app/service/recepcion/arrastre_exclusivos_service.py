from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


class ArrastreExcluidosService:
    """
    Ejecuta el arrastre de excluidos NO vencidos desde la recepción anterior inmediata
    (mismo prestador+obra social) hacia la recepción actual, renumerando orden_lote 1.K.

    Importante:
    - Solo corre si la recepción actual está vacía.
    - Filtra vencidas usando fecha_presentacion_actual - 60 días.
    """

    @staticmethod
    def run(session: Session, *, recepcion_id: int) -> int:
        stmt = text("SELECT fn_arrastrar_excluidos_previos(:rid) AS moved")
        moved = session.execute(stmt, {"rid": int(recepcion_id)}).scalar_one()
        try:
            return int(moved or 0)
        except Exception:
            return 0