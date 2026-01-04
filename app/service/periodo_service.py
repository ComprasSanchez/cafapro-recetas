from __future__ import annotations

from datetime import date
from typing import Sequence

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Periodo


class PeriodoService:
    @staticmethod
    def list(session: Session) -> Sequence[Periodo]:
        stmt = select(Periodo).order_by(Periodo.anio.desc(), Periodo.mes.desc(), Periodo.quincena.desc())
        return session.execute(stmt).scalars().all()

    @staticmethod
    def create(
        session: Session,
        *,
        anio: int,
        mes: int,
        quincena: int
    ) -> None:
        if quincena not in (1, 2):
            raise ValueError("quincena debe ser 1 o 2")
        if not (1 <= mes <= 12):
            raise ValueError("mes debe estar entre 1 y 12")

        existente = session.execute(
            select(Periodo).where(
                and_(
                    Periodo.anio == anio,
                    Periodo.mes == mes,
                    Periodo.quincena == quincena,
                )
            )
        ).scalar_one_or_none()

        if existente:
            raise ValueError("Ese período ya existe.")

        p = Periodo(
            anio=anio,
            mes=mes,
            quincena=quincena,
        )
        session.add(p)

        try:
            session.flush()  # genera periodo_id, pero no hace falta devolverlo
        except IntegrityError as e:
            raise ValueError("Ya existe un período con ese anio/mes/quincena") from e

    @staticmethod
    def delete(session: Session, periodo_id: int) -> None:
        p = session.get(Periodo, periodo_id)
        if not p:
            raise ValueError("No existe el período")
        session.delete(p)
