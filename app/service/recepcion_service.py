from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

from app.db.models import Recepcion, EstadoRecepcion
from app.db.models import ObraSocial
from app.db.models import Periodo
from app.db.models import Prestador

@dataclass(frozen=True)
class RecepcionListItem:
    recepcion_id: int
    numero: int
    obra_social: str
    periodo: str
    prestador: str
    estado: str
    fecha_recepcion: object
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
    fecha_recepcion: Optional[date]

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
        # Pediste: numero recepcion, obra social, fecha (yyyy-mm-dd)
        rows = s.execute(
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Recepcion.fecha_recepcion,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .where(
                Recepcion.periodo_id == int(periodo_id),
                Recepcion.prestador_id == int(prestador_id),
            )
            .order_by(Recepcion.fecha_recepcion.desc(), Recepcion.numero.desc(), Recepcion.recepcion_id.desc())
        ).all()

        return [
            RecepcionRowItem(
                recepcion_id=r[0],
                numero=r[1],
                obra_social=r[2] or "",
                fecha_recepcion=r[3],
            )
            for r in rows
        ]

    @staticmethod
    def list(s: Session) -> list[RecepcionListItem]:
        rows = s.execute(
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Periodo.anio, Periodo.mes, Periodo.quincena,
                Prestador.codigo, Prestador.nombre,
                EstadoRecepcion.descripcion,
                Recepcion.fecha_recepcion,
                Recepcion.creado_en,
                Prestador.imed,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .join(Periodo, Periodo.periodo_id == Recepcion.periodo_id)
            .join(Prestador, Prestador.prestador_id == Recepcion.prestador_id)
            .join(EstadoRecepcion, EstadoRecepcion.estado_recepcion_id == Recepcion.estado_recepcion_id)
            .order_by(Recepcion.recepcion_id.desc())
        ).all()

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
                    obra_social=os_nombre,
                    periodo=periodo_txt,
                    prestador=prestador_txt,
                    estado=estado,
                    fecha_recepcion=fecha_rec,
                    creado_en=creado_en,
                    imed=imed
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
        fecha_recepcion,
        observaciones: str | None = None,
        creado_por_usuario_id: int | None = None,
    ) -> Recepcion:
        if not estado_recepcion_id:
            raise ValueError("estado_recepcion es obligatorio.")

        rec = Recepcion(
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion_id=estado_recepcion_id,
            fecha_recepcion=fecha_recepcion,
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
