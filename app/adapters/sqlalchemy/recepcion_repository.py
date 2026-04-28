from __future__ import annotations

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.orm import Session

from app.db.models import Archivo, Asociacion, EstadoRecepcion, ObraSocial, Periodo, Prestador, Recepcion


class RecepcionRepository:
    @staticmethod
    def list_prestadores_con_recepcion(session: Session, *, periodo_id: int):
        return session.execute(
            select(
                Prestador.prestador_id,
                Prestador.nombre,
                Prestador.codigo,
                Prestador.imed,
                func.count(distinct(Recepcion.recepcion_id)).label("cantidad"),
            )
            .join(Recepcion, Recepcion.prestador_id == Prestador.prestador_id)
            .where(
                Prestador.activo.is_(True),
                Recepcion.periodo_id == int(periodo_id),
            )
            .group_by(Prestador.prestador_id, Prestador.nombre, Prestador.codigo, Prestador.imed)
            .order_by(Prestador.nombre.nulls_last(), Prestador.codigo)
        ).all()

    @staticmethod
    def list_recepciones_por_periodo_prestador(session: Session, *, periodo_id: int, prestador_id: int):
        return session.execute(
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Recepcion.fecha_presentacion,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .where(
                Recepcion.periodo_id == int(periodo_id),
                Recepcion.prestador_id == int(prestador_id),
            )
            .order_by(Recepcion.fecha_presentacion.desc(), Recepcion.numero.desc(), Recepcion.recepcion_id.desc())
        ).all()

    @staticmethod
    def list_with_details(session: Session, *, include_closed: bool):
        q = (
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Periodo.anio,
                Periodo.mes,
                Periodo.quincena,
                Prestador.codigo,
                Prestador.nombre,
                EstadoRecepcion.descripcion,
                Recepcion.fecha_presentacion,
                Recepcion.creado_en,
                Prestador.imed,
                ObraSocial.validador,
                ObraSocial.dias_vencimiento,
                ObraSocial.codigo_financiador,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .join(Periodo, Periodo.periodo_id == Recepcion.periodo_id)
            .join(Prestador, Prestador.prestador_id == Recepcion.prestador_id)
            .join(EstadoRecepcion, EstadoRecepcion.estado_recepcion_id == Recepcion.estado_recepcion_id)
        )

        if not include_closed:
            q = q.where(Recepcion.estado_recepcion_id == 1)

        return session.execute(q.order_by(Recepcion.recepcion_id.desc())).all()

    @staticmethod
    def exists_same_scope(
        session: Session,
        *,
        obra_social_id: int,
        periodo_id: int,
        prestador_id: int,
    ) -> bool:
        existe = session.execute(
            select(Recepcion.recepcion_id).where(
                Recepcion.obra_social_id == int(obra_social_id),
                Recepcion.periodo_id == int(periodo_id),
                Recepcion.prestador_id == int(prestador_id),
            )
        ).scalar_one_or_none()

        return existe is not None

    @staticmethod
    def exists_open_by_obra_prestador(
        session: Session,
        *,
        obra_social_id: int,
        prestador_id: int,
    ) -> bool:
        existe = session.execute(
            select(Recepcion.recepcion_id).where(
                Recepcion.obra_social_id == int(obra_social_id),
                Recepcion.prestador_id == int(prestador_id),
                Recepcion.estado_recepcion_id == 1,
            )
        ).scalar_one_or_none()

        return existe is not None

    @staticmethod
    def create(
        session: Session,
        *,
        obra_social_id: int,
        periodo_id: int,
        prestador_id: int,
        estado_recepcion_id: int,
        fecha_presentacion,
        observaciones: str | None,
        creado_por_usuario_id: int | None,
    ) -> Recepcion:
        rec = Recepcion(
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion_id=int(estado_recepcion_id),
            fecha_presentacion=fecha_presentacion,
            observaciones=observaciones,
            creado_por_usuario_id=creado_por_usuario_id,
        )

        session.add(rec)
        session.flush()
        session.refresh(rec)
        return rec

    @staticmethod
    def get(session: Session, *, recepcion_id: int) -> Recepcion | None:
        return session.get(Recepcion, int(recepcion_id))

    @staticmethod
    def get_cierre_context(session: Session, *, recepcion_id: int):
        return session.execute(
            select(Recepcion, ObraSocial.dias_vencimiento)
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .where(Recepcion.recepcion_id == int(recepcion_id))
        ).first()

    @staticmethod
    def list_archivos_sin_asociacion(session: Session, *, recepcion_id: int) -> list[Archivo]:
        return (
            session.execute(
                select(Archivo)
                .outerjoin(
                    Asociacion,
                    and_(
                        Asociacion.archivo_id == Archivo.archivo_id,
                        Asociacion.vigente.is_(True),
                    ),
                )
                .where(
                    Archivo.recepcion_id == int(recepcion_id),
                    Asociacion.asociacion_id.is_(None),
                )
            )
            .scalars()
            .all()
        )
