from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import MotivoDebito, LadoEnum, SiNoEnum


class MotivosDebitosService:

    # ---------------------------------
    # LIST
    # ---------------------------------
    @staticmethod
    def list(
        session: Session,
        lado: str | None = None,
        activo: bool | None = None,
    ) -> list[MotivoDebito]:

        stmt = select(MotivoDebito)

        if lado:
            stmt = stmt.where(MotivoDebito.lado == LadoEnum(lado))

        if activo is not None:
            stmt = stmt.where(MotivoDebito.activo.is_(activo))

        stmt = stmt.order_by(MotivoDebito.codigo.asc())

        return session.execute(stmt).scalars().all()

    # ---------------------------------
    # CREATE
    # ---------------------------------
    @staticmethod
    def create(
        session: Session,
        descripcion: str,
        lado: str,
    ) -> MotivoDebito:

        descripcion = descripcion.strip()

        nuevo = MotivoDebito(
            descripcion=descripcion,
            lado=LadoEnum(lado),
            excluyente=SiNoEnum.N,  # default
            codigo=descripcion.upper().replace(" ", "_"),
            activo=True,
        )

        session.add(nuevo)
        session.flush()  # para obtener ID sin commit

        return nuevo

    # ---------------------------------
    # TOGGLE BAJA LÓGICA
    # ---------------------------------
    @staticmethod
    def toggle_activo(
        session: Session,
        motivo_id: int,
    ) -> None:

        motivo = session.get(MotivoDebito, int(motivo_id))
        if not motivo:
            raise ValueError("Motivo no encontrado")

        motivo.activo = not motivo.activo

    # ---------------------------------
    # GET BY ID
    # ---------------------------------
    @staticmethod
    def get(session: Session, motivo_id: int) -> MotivoDebito | None:
        return session.get(MotivoDebito, int(motivo_id))