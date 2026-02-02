from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import ObraSocial

@dataclass(frozen=True)
class ObraSocialItem:
    obra_social_id: int
    nombre: str
    codigo: str

class ObraSocialService:
    @staticmethod
    def list(s: Session) -> list[ObraSocialItem]:
        rows = s.execute(
            select(ObraSocial.obra_social_id, ObraSocial.nombre, ObraSocial.codigo)
            .where(ObraSocial.activo.is_(True))
            .order_by(ObraSocial.nombre)
        ).all()
        return [ObraSocialItem(r[0], r[1], r[2]) for r in rows]