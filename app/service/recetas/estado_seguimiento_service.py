from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import EstadoSeguimiento

class EstadoSeguimientoService:
    @staticmethod
    def list(session: Session) -> list[type[EstadoSeguimiento]]:
        return session.query(EstadoSeguimiento).order_by(EstadoSeguimiento.descripcion.asc()).all()
