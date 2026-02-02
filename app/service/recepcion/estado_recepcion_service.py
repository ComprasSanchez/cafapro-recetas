from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import EstadoRecepcion


class EstadoRecepcionService:
    @staticmethod
    def list(session: Session) -> list[type[EstadoRecepcion]]:
        return session.query(EstadoRecepcion).order_by(EstadoRecepcion.descripcion.asc()).all()