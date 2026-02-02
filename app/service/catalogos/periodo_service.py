from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Optional

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Periodo


@dataclass(frozen=True)
class PeriodoItem:
    periodo_id: int
    anio: int
    mes: int
    quincena: int
    activo: bool

    @property
    def label(self) -> str:
        # "2026-01 Q1"
        return f"{self.anio}-{self.mes:02d} Q{self.quincena}"


class PeriodoService:
    # ---------------------
    # LIST
    # ---------------------
    @staticmethod
    def list(session: Session, *, solo_activos: bool = False) -> Sequence[PeriodoItem]:
        stmt = select(
            Periodo.periodo_id,
            Periodo.anio,
            Periodo.mes,
            Periodo.quincena,
            Periodo.activo,
        )

        if solo_activos:
            stmt = stmt.where(Periodo.activo.is_(True))

        stmt = stmt.order_by(
            Periodo.anio.desc(),
            Periodo.mes.desc(),
            Periodo.quincena.desc(),
        )

        rows = session.execute(stmt).all()
        return [
            PeriodoItem(
                periodo_id=r[0],
                anio=r[1],
                mes=r[2],
                quincena=r[3],
                activo=bool(r[4]),
            )
            for r in rows
        ]

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(session: Session, periodo_id: int) -> Periodo | None:
        return session.get(Periodo, int(periodo_id))

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        session: Session,
        *,
        anio: int,
        mes: int,
        quincena: int,
    ) -> Periodo:
        if quincena not in (1, 2):
            raise ValueError("quincena debe ser 1 o 2")
        if not (1 <= int(mes) <= 12):
            raise ValueError("mes debe estar entre 1 y 12")

        existente = session.execute(
            select(Periodo.periodo_id).where(
                and_(
                    Periodo.anio == int(anio),
                    Periodo.mes == int(mes),
                    Periodo.quincena == int(quincena),
                )
            ).limit(1)
        ).scalar_one_or_none()

        if existente:
            raise ValueError("Ese período ya existe.")

        p = Periodo(
            anio=int(anio),
            mes=int(mes),
            quincena=int(quincena),
            activo=True,
        )
        session.add(p)

        try:
            session.flush()
            session.refresh(p)
        except IntegrityError as e:
            raise ValueError("Ya existe un período con ese anio/mes/quincena") from e

        return p

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        session: Session,
        *,
        periodo_id: int,
        anio: int,
        mes: int,
        quincena: int,
    ) -> None:
        p = session.get(Periodo, int(periodo_id))
        if not p:
            raise ValueError("No existe el período")

        if quincena not in (1, 2):
            raise ValueError("quincena debe ser 1 o 2")
        if not (1 <= int(mes) <= 12):
            raise ValueError("mes debe estar entre 1 y 12")

        # validar que no choque contra otro período
        existe = session.execute(
            select(Periodo.periodo_id).where(
                and_(
                    Periodo.anio == int(anio),
                    Periodo.mes == int(mes),
                    Periodo.quincena == int(quincena),
                    Periodo.periodo_id != int(periodo_id),
                )
            ).limit(1)
        ).scalar_one_or_none()

        if existe:
            raise ValueError("Ya existe otro período con ese anio/mes/quincena")

        p.anio = int(anio)
        p.mes = int(mes)
        p.quincena = int(quincena)

        try:
            session.flush()
        except IntegrityError as e:
            raise ValueError("Ya existe otro período con ese anio/mes/quincena") from e

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(session: Session, periodo_id: int) -> None:
        p = session.get(Periodo, int(periodo_id))
        if not p:
            raise ValueError("No existe el período")
        p.activo = False

    # ---------------------
    # RESTORE
    # ---------------------
    @staticmethod
    def restore(session: Session, periodo_id: int) -> None:
        p = session.get(Periodo, int(periodo_id))
        if not p:
            raise ValueError("No existe el período")
        p.activo = True
