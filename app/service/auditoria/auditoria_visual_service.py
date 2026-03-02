from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload


from sqlalchemy.orm import Session

from app.db.models import (
    Asociacion, Recetas, Archivo, Troqueles, ArchivoDetalle, Debitos, MotivoDebito, Vendedores
)
from app.service.recetas.historial_receta_service import HistorialRecetaService


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
    motivos_frente: List[type[MotivoDebito]]
    motivos_dorso: List[type[MotivoDebito]]
    has_historial_debitada: bool
    vendedor: type[Vendedores] | None


class AuditoriaVisualService:

    @staticmethod
    def load_by_asociacion_id(session: Session, asociacion_id: int) -> AuditoriaVisualData:
        stmt = (
            select(Asociacion)
            .options(
                selectinload(Asociacion.receta)
                .selectinload(Recetas.troqueles),

                selectinload(Asociacion.receta)
                .selectinload(Recetas.debitos)
                .selectinload(Debitos.motivo_debito),

                selectinload(Asociacion.archivo)
                .selectinload(Archivo.archivo_detalles),
            )
            .where(Asociacion.asociacion_id == asociacion_id)
        )

        asociacion = session.execute(stmt).scalar_one_or_none()

        if not asociacion:
            raise ValueError("No existe asociación")

        receta = asociacion.receta
        archivo = asociacion.archivo

        troqueles = receta.troqueles
        archivo_detalles = archivo.archivo_detalles

        debitos = [
            DebitoRow(
                debito_id=d.debito_id,
                motivo_debito_id=d.motivo_debito_id,
                motivo_codigo=d.motivo_debito.codigo,
                motivo_descripcion=d.motivo_debito.descripcion,
                lado=str(d.motivo_debito.lado),
                excluyente=str(d.motivo_debito.excluyente),
                detalle=d.detalle,
            )
            for d in receta.debitos
        ]

        motivos = session.query(MotivoDebito).order_by(
            MotivoDebito.motivo_debito_id
        ).all()

        motivos_frente = [m for m in motivos if m.lado == "F"]
        motivos_dorso = [m for m in motivos if m.lado == "D"]

        has_historial = HistorialRecetaService.has_historial_debitada(
            session,
            archivo_id=archivo.archivo_id
        )

        vendedor = None
        if receta and receta.vendedor_id:
            vendedor = session.get(Vendedores, receta.vendedor_id)

        return AuditoriaVisualData(
            asociacion=asociacion,
            receta=receta,
            archivo=archivo,
            troqueles=troqueles,
            archivo_detalles=archivo_detalles,
            debitos=debitos,
            motivos_frente=motivos_frente,
            motivos_dorso=motivos_dorso,
            has_historial_debitada=has_historial,
            vendedor=vendedor
        )
