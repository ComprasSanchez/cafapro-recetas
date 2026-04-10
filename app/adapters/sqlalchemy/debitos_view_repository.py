from __future__ import annotations

from datetime import date

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Periodo, Recepcion, Recetas
from app.db.view import VwArchivoRecetaDebitos


class DebitosViewRepository:
    @staticmethod
    def list_recepciones(session: Session):
        return (
            session.query(
                VwArchivoRecetaDebitos.recepcion_id,
                VwArchivoRecetaDebitos.recepcion_numero,
            )
            .filter(VwArchivoRecetaDebitos.recepcion_id.isnot(None))
            .distinct()
            .order_by(VwArchivoRecetaDebitos.recepcion_numero.asc())
            .all()
        )

    @staticmethod
    def list_debitos(
        session: Session,
        *,
        recepcion_id: int | None,
        fecha_auditoria: date | None,
    ) -> list[VwArchivoRecetaDebitos]:
        q = session.query(VwArchivoRecetaDebitos)

        if recepcion_id is not None:
            q = q.filter(VwArchivoRecetaDebitos.recepcion_id == int(recepcion_id))

        if fecha_auditoria is not None:
            q = q.filter(sa.cast(VwArchivoRecetaDebitos.creado_en, sa.Date) == fecha_auditoria)

        q = q.order_by(
            VwArchivoRecetaDebitos.fecha.asc(),
            VwArchivoRecetaDebitos.hora.asc(),
            VwArchivoRecetaDebitos.orden_lote.asc(),
        )

        return q.all()

    @staticmethod
    def list_wrong_debitos_month(
        session: Session,
        *,
        obra_social_id: int,
        anio: int,
        mes: int,
    ) -> list[VwArchivoRecetaDebitos]:
        q = (
            session.query(VwArchivoRecetaDebitos)
            .join(Recepcion, Recepcion.recepcion_id == VwArchivoRecetaDebitos.recepcion_id)
            .join(Periodo, Periodo.periodo_id == Recepcion.periodo_id)
            .filter(
                Recepcion.obra_social_id == int(obra_social_id),
                Periodo.anio == int(anio),
                Periodo.mes == int(mes),
                VwArchivoRecetaDebitos.motivo_debito_id == 9,
            )
            .order_by(
                VwArchivoRecetaDebitos.recepcion_numero.asc(),
                VwArchivoRecetaDebitos.orden_lote.asc(),
                VwArchivoRecetaDebitos.nro_receta.asc(),
            )
        )

        return q.all()

    @staticmethod
    def get_periodo_parts(session: Session, *, recepcion_id: int) -> tuple[int, int, int] | None:
        row = (
            session.query(Periodo.anio, Periodo.mes, Periodo.quincena)
            .join(Recepcion, Recepcion.periodo_id == Periodo.periodo_id)
            .filter(Recepcion.recepcion_id == int(recepcion_id))
            .first()
        )

        if not row:
            return None

        anio, mes, quincena = row
        return int(anio), int(mes), int(quincena)

    @staticmethod
    def get_recetas_paths(session: Session, *, receta_ids: set[int]):
        return session.execute(
            select(
                Recetas.receta_id,
                Recetas.ubicacion_frente,
                Recetas.ubicacion_dorso,
            ).where(Recetas.receta_id.in_(receta_ids))
        ).all()
