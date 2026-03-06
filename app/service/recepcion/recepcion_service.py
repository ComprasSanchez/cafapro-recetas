from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from typing import Optional

from sqlalchemy import select, func, distinct, update, and_
from sqlalchemy.orm import Session

from app.db.models import Recepcion, EstadoRecepcion, ObraSocial, Periodo, Prestador, Archivo, Asociacion


@dataclass(frozen=True)
class RecepcionListItem:
    recepcion_id: int
    numero: int
    obra_social: str
    periodo: str
    prestador: str
    estado: str
    fecha_presentacion: object
    creado_en: Optional[object]
    imed: str

@dataclass(frozen=True)
class PrestadorConRecepcionesItem:
    prestador_id: int
    nombre: str
    codigo: str
    imed: str
    cantidad_recepciones: int


@dataclass(frozen=True)
class RecepcionRowItem:
    recepcion_id: int
    numero: int
    obra_social: str
    fecha_presentacion: Optional[date]

class RecepcionService:
    @staticmethod
    def list_prestadores_con_recepcion(s: Session, *, periodo_id: int) -> list[PrestadorConRecepcionesItem]:
        rows = s.execute(
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

        out: list[PrestadorConRecepcionesItem] = []
        for pid, nom, cod, imed, cant in rows:
            out.append(
                PrestadorConRecepcionesItem(
                    prestador_id=pid,
                    nombre=nom or "(sin nombre)",
                    codigo=cod or "",
                    imed=imed or "",
                    cantidad_recepciones=int(cant or 0),
                )
            )
        return out

    @staticmethod
    def list_recepciones(s: Session, *, periodo_id: int, prestador_id: int) -> list[RecepcionRowItem]:
        rows = s.execute(
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

        return [
            RecepcionRowItem(
                recepcion_id=r[0],
                numero=r[1],
                obra_social=r[2] or "",
                fecha_presentacion=r[3],
            )
            for r in rows
        ]

    @staticmethod
    @staticmethod
    def list(s: Session, *, all: bool = True) -> list[RecepcionListItem]:
        q = (
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Periodo.anio, Periodo.mes, Periodo.quincena,
                Prestador.codigo, Prestador.nombre,
                EstadoRecepcion.descripcion,
                Recepcion.fecha_presentacion,
                Recepcion.creado_en,
                Prestador.imed,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .join(Periodo, Periodo.periodo_id == Recepcion.periodo_id)
            .join(Prestador, Prestador.prestador_id == Recepcion.prestador_id)
            .join(EstadoRecepcion, EstadoRecepcion.estado_recepcion_id == Recepcion.estado_recepcion_id)
        )

        if not all:
            q = q.where(Recepcion.estado_recepcion_id == 1)

        rows = s.execute(q.order_by(Recepcion.recepcion_id.desc())).all()
        out: list[RecepcionListItem] = []
        for r in rows:
            (rid, numero, os_nombre, anio, mes, quin, pres_cod, pres_nom,
             estado, fecha_rec, creado_en, imed) = r
            periodo_txt = f"{anio}-{mes:02d} Q{quin}"
            prestador_txt = f"{pres_nom or ''}"
            out.append(
                RecepcionListItem(
                    recepcion_id=rid,
                    numero=numero,
                    obra_social=os_nombre or "",
                    periodo=periodo_txt,
                    prestador=prestador_txt,
                    estado=estado or "",
                    fecha_presentacion=fecha_rec,
                    creado_en=creado_en,
                    imed=imed or "",
                )
            )
        return out

    @staticmethod
    def create(
            s: Session,
            obra_social_id: int,
            periodo_id: int,
            prestador_id: int,
            estado_recepcion_id: int,
            fecha_presentacion,
            observaciones: str | None = None,
            creado_por_usuario_id: int | None = None,
    ) -> Recepcion:

        if not estado_recepcion_id:
            raise ValueError("estado_recepcion es obligatorio.")

        # ---------------------------------
        # verificar si ya existe recepción
        # ---------------------------------

        existe = s.execute(
            select(Recepcion.recepcion_id)
            .where(
                Recepcion.obra_social_id == int(obra_social_id),
                Recepcion.periodo_id == int(periodo_id),
                Recepcion.prestador_id == int(prestador_id),
            )
        ).scalar_one_or_none()

        if existe:
            raise RuntimeError(
                "Ya existe una recepción para esta obra social, período y prestador."
            )

        # ---------------------------------
        # crear recepción
        # ---------------------------------

        rec = Recepcion(
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion_id=int(estado_recepcion_id),
            fecha_presentacion=fecha_presentacion,
            observaciones=observaciones,
            creado_por_usuario_id=creado_por_usuario_id,
        )

        s.add(rec)
        s.flush()
        s.refresh(rec)

        return rec

    @staticmethod
    def delete(s: Session, recepcion_id: int) -> None:
        rec = s.get(Recepcion, recepcion_id)
        if not rec:
            raise ValueError("La recepción no existe.")
        s.delete(rec)


    @staticmethod
    def cerrar_recepcion(s: Session, recepcion_id: int) -> None:
        rec = (
            s.execute(select(Recepcion).where(Recepcion.recepcion_id == int(recepcion_id)))
            .scalar_one_or_none()
        )
        if not rec:
            raise RuntimeError(f"No existe la recepción {recepcion_id}")

        cutoff = rec.fecha_presentacion - timedelta(days=60)

        # Archivos de la recepción que NO tienen asociación vigente
        archivos_sin_asoc = (
            s.execute(
                select(Archivo)
                .outerjoin(
                    Asociacion,
                    and_(
                        Asociacion.archivo_id == Archivo.archivo_id,
                        Asociacion.vigente.is_(True),
                    )
                )
                .where(
                    Archivo.recepcion_id == int(recepcion_id),
                    Asociacion.asociacion_id.is_(None),  # <- no hay vigente
                )
            )
            .scalars()
            .all()
        )

        for a in archivos_sin_asoc:
            # fecha y hora siempre vienen
            archivo_ts = datetime.combine(a.fecha, a.hora)
            if archivo_ts < cutoff:
                a.vencido = True

        rec.estado_recepcion_id = 2
        s.flush()
