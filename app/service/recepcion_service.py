from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Recepcion
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

class RecepcionService:
    @staticmethod
    def list(s: Session) -> list[RecepcionListItem]:
        rows = s.execute(
            select(
                Recepcion.recepcion_id,
                Recepcion.numero,
                ObraSocial.nombre,
                Periodo.anio, Periodo.mes, Periodo.quincena,
                Prestador.codigo, Prestador.nombre,
                Recepcion.estado_recepcion,
                Recepcion.fecha_recepcion,
                Recepcion.creado_en,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Recepcion.obra_social_id)
            .join(Periodo, Periodo.periodo_id == Recepcion.periodo_id)
            .join(Prestador, Prestador.prestador_id == Recepcion.prestador_id)
            .order_by(Recepcion.recepcion_id.desc())
        ).all()

        out: list[RecepcionListItem] = []
        for r in rows:
            (rid, numero, os_nombre, anio, mes, quin, pres_cod, pres_nom,
             estado, fecha_rec, creado_en) = r
            periodo_txt = f"{anio}-{mes:02d} Q{quin}"
            prestador_txt = f"{pres_cod} - {pres_nom or ''}".strip(" -")
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
                )
            )
        return out

    @staticmethod
    def create(
        s: Session,
        obra_social_id: int,
        periodo_id: int,
        prestador_id: int,
        estado_recepcion: str,
        fecha_recepcion,
        observaciones: str | None = None,
        creado_por_usuario_id: int | None = None,
    ) -> Recepcion:
        if not estado_recepcion:
            raise ValueError("estado_recepcion es obligatorio.")

        rec = Recepcion(
            obra_social_id=int(obra_social_id),
            periodo_id=int(periodo_id),
            prestador_id=int(prestador_id),
            estado_recepcion=estado_recepcion,
            fecha_recepcion=fecha_recepcion,
            observaciones=observaciones,
            creado_por_usuario_id=creado_por_usuario_id,
            # numero NO lo seteamos: lo pone la DB con la secuencia (server_default)
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
