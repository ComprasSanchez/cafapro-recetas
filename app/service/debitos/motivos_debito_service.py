from sqlalchemy.orm import Session

from app.db.models import (
    MotivoDebito
)



class MotivosDebitosService:

    @staticmethod
    def list_motivos(session: Session, lado: str | None = None) -> list[type[MotivoDebito]]:
        q = session.query(MotivoDebito)
        if lado:
            q = q.filter(MotivoDebito.lado == lado)
        return q.order_by(MotivoDebito.codigo.asc()).all()
