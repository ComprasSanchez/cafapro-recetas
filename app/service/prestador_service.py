from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Prestador

@dataclass(frozen=True)
class PrestadorItem:
    prestador_id: int
    nombre: str
    codigo: str

class PrestadorService:
    @staticmethod
    def list(s: Session) -> list[PrestadorItem]:
        rows = s.execute(
            select(Prestador.prestador_id, Prestador.nombre, Prestador.codigo)
            .where(Prestador.activo.is_(True))
            .order_by(Prestador.nombre.nulls_last(), Prestador.codigo)
        ).all()
        return [PrestadorItem(r[0], r[1] or "(sin nombre)", r[2]) for r in rows]
