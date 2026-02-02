from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from app.db.models import Debitos


@dataclass(frozen=True)
class DebitoInput:
    motivo_debito_id: int
    detalle: str | None = None


class DebitosService:
    @staticmethod
    def replace_for_receta(session: Session, receta_id: int, items: Iterable[DebitoInput]) -> None:
        # borra existentes
        session.query(Debitos).filter(Debitos.receta_id == receta_id).delete(synchronize_session=False)

        # inserta nuevos
        for it in items:
            session.add(Debitos(
                receta_id=receta_id,
                motivo_debito_id=int(it.motivo_debito_id),
                detalle=(it.detalle or None),
            ))
