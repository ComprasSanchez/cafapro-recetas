from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models import (
    Asociacion, Recetas, Archivo, Troqueles, ArchivoDetalle, Debitos, MotivoDebito
)


@dataclass(frozen=True)
class DebitoRow:
    debito_id: int
    motivo_debito_id: int
    motivo_codigo: str
    motivo_descripcion: str
    lado: str
    excluyente: str
    detalle: Optional[str]


@dataclass(frozen=True)
class AuditoriaVisualData:
    asociacion: type[Asociacion]
    receta: type[Recetas]
    archivo: type[Archivo]
    troqueles: List[type[Troqueles]]
    archivo_detalles: List[type[ArchivoDetalle]]
    debitos: List[DebitoRow]
    total_troqueles: Decimal


class AuditoriaVisualService:
    @staticmethod
    def load_by_asociacion_id(session: Session, asociacion_id: int) -> AuditoriaVisualData:
        asociacion = session.get(Asociacion, asociacion_id)
        if not asociacion:
            raise ValueError(f"No existe Asociacion con id={asociacion_id}")

        if not getattr(asociacion, "vigente", True):
            # Redirigir a la asociación vigente del mismo archivo (lo operativo)
            asoc_vig = (
                session.query(Asociacion)
                .filter(
                    Asociacion.archivo_id == asociacion.archivo_id,
                    Asociacion.vigente.is_(True),
                )
                .order_by(Asociacion.asociacion_id.desc())
                .first()
            )
            if not asoc_vig:
                raise ValueError(
                    f"La asociación {asociacion_id} no es vigente y no existe una vigente para archivo_id={asociacion.archivo_id}"
                )
            asociacion = asoc_vig

        # 2) Receta + Archivo
        receta = session.get(Recetas, asociacion.receta_id)
        if not receta:
            raise ValueError(
                f"Asociacion {asociacion.asociacion_id} apunta a receta_id inexistente={asociacion.receta_id}"
            )

        archivo = session.get(Archivo, asociacion.archivo_id)
        if not archivo:
            raise ValueError(
                f"Asociacion {asociacion.asociacion_id} apunta a archivo_id inexistente={asociacion.archivo_id}"
            )

        # 3) Troqueles (de la receta vigente)
        troqueles = (
            session.query(Troqueles)
            .filter(Troqueles.receta_id == receta.receta_id)
            .order_by(Troqueles.troquel_id.asc())
            .all()
        )

        # 4) ArchivoDetalle (del archivo)
        archivo_detalles = (
            session.query(ArchivoDetalle)
            .filter(ArchivoDetalle.archivo_id == archivo.archivo_id)
            .order_by(ArchivoDetalle.archivo_detalle_id.asc())
            .all()
        )

        # 5) Debitos + MotivoDebito (de la receta)
        rows = (
            session.query(
                Debitos.debito_id,
                Debitos.motivo_debito_id,
                MotivoDebito.codigo,
                MotivoDebito.descripcion,
                MotivoDebito.lado,
                MotivoDebito.excluyente,
                Debitos.detalle,
            )
            .join(MotivoDebito, MotivoDebito.motivo_debito_id == Debitos.motivo_debito_id)
            .filter(Debitos.receta_id == receta.receta_id)
            .order_by(Debitos.debito_id.asc())
            .all()
        )

        debitos = [
            DebitoRow(
                debito_id=r[0],
                motivo_debito_id=r[1],
                motivo_codigo=r[2],
                motivo_descripcion=r[3],
                lado=str(r[4]),
                excluyente=str(r[5]),
                detalle=r[6],
            )
            for r in rows
        ]

        # 6) Total troqueles = SUM(monto * cantidad)
        total = Decimal("0")
        for t in troqueles:
            monto = Decimal(str(getattr(t, "monto", 0) or 0))
            cant = int(getattr(t, "cantidad", 0) or 0)
            total += (monto * Decimal(cant))

        return AuditoriaVisualData(
            asociacion=asociacion,
            receta=receta,
            archivo=archivo,
            troqueles=troqueles,
            archivo_detalles=archivo_detalles,
            debitos=debitos,
            total_troqueles=total,
        )
