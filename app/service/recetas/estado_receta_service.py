from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import EstadoReceta


class EstadoRecetaService:
    @staticmethod
    def list(session: Session) -> list[type[EstadoReceta]]:
        return session.query(EstadoReceta).order_by(EstadoReceta.descripcion.asc()).all()