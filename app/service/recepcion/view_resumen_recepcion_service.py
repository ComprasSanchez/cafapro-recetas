
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import Prestador
from app.db.view import VwResumenRecepcionPrestador
from app.service.recepcion.recepcion_service import RecepcionService

@dataclass(frozen=True)
class ResumenRecepcionItem:
    cantidad_recetas: int
    total_general: object
    total_importe_obs: object
    total_a_cargo_entidad: object

@dataclass(frozen=True)
class PrestadorResumenItem:
    prestador_id: int
    prestador: str
    total_general: object
    total_importe_obs: object
    total_a_cargo_entidad: object



class ViewResumenRecepcionService(RecepcionService):
    @staticmethod
    def get_resumen_recepcion(s: Session, *, recepcion_id: int) -> ResumenRecepcionItem | None:
        row = s.execute(
            select(
                VwResumenRecepcionPrestador.cantidad_recetas,
                VwResumenRecepcionPrestador.total_general,
                VwResumenRecepcionPrestador.total_importe_obs,
                VwResumenRecepcionPrestador.total_a_cargo_entidad,
            ).where(VwResumenRecepcionPrestador.recepcion_id == int(recepcion_id))
        ).first()

        if not row:
            return None

        return ResumenRecepcionItem(
            cantidad_recetas=int(row[0] or 0),
            total_general=row[1] or 0,
            total_importe_obs=row[2] or 0,
            total_a_cargo_entidad=row[3] or 0,
        )

    @staticmethod
    def list_prestadores_resumen(s: Session, *, periodo_id: int) -> list[PrestadorResumenItem]:
        # Sumamos los totales de la VIEW por prestador dentro del período.
        # Si un prestador tiene N recepciones, la VIEW tiene N filas (1 por recepcion) y esto suma perfecto.
        rows = s.execute(
            select(
                Prestador.prestador_id,
                Prestador.nombre,
                func.coalesce(func.sum(VwResumenRecepcionPrestador.total_general), 0).label("total_general"),
                func.coalesce(func.sum(VwResumenRecepcionPrestador.total_importe_obs), 0).label("total_obs"),
                func.coalesce(func.sum(VwResumenRecepcionPrestador.total_a_cargo_entidad), 0).label("total_cargo"),
            )
            .join(VwResumenRecepcionPrestador, VwResumenRecepcionPrestador.prestador_id == Prestador.prestador_id)
            .where(
                Prestador.activo.is_(True),
                VwResumenRecepcionPrestador.periodo_id == int(periodo_id),
            )
            .group_by(Prestador.prestador_id, Prestador.nombre)
            .order_by(Prestador.nombre.nulls_last())
        ).all()

        out: list[PrestadorResumenItem] = []
        for pid, nombre, tg, tobs, tcargo in rows:
            out.append(
                PrestadorResumenItem(
                    prestador_id=pid,
                    prestador=nombre or "(sin nombre)",
                    total_general=tg,
                    total_importe_obs=tobs,
                    total_a_cargo_entidad=tcargo,
                )
            )
        return out
