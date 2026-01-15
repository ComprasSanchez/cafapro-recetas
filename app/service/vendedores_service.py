from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Vendedores


class VendedoresService:
    @staticmethod
    def list(session: Session) -> list[type[Vendedores]]:
        return (
            session.query(Vendedores)
            .order_by(Vendedores.descripcion.asc())
            .all()
        )

    @staticmethod
    def get(session: Session, vendedor_id: int) -> Vendedores | None:
        return session.get(Vendedores, vendedor_id)
