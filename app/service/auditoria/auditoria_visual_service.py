from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    Asociacion, Recetas, Archivo, Troqueles, ArchivoDetalle, Debitos, MotivoDebito
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


class AuditoriaVisualService:
    @staticmethod
    def load_by_asociacion_id(session: Session, asociacion_id: int) -> AuditoriaVisualData:
        asociacion = session.get(Asociacion, asociacion_id)
        if not asociacion:
            raise ValueError(f"No existe Asociacion con id={asociacion_id}")

        if not getattr(asociacion, "vigente", True):
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
                raise ValueError("No existe asociación vigente")
            asociacion = asoc_vig

        receta = session.get(Recetas, asociacion.receta_id)
        archivo = session.get(Archivo, asociacion.archivo_id)

        # 🔹 Troqueles
        troqueles = (
            session.query(Troqueles)
            .filter(Troqueles.receta_id == receta.receta_id)
            .order_by(Troqueles.troquel_id.asc())
            .all()
        )

        # 🔹 ArchivoDetalle
        archivo_detalles = (
            session.query(ArchivoDetalle)
            .filter(ArchivoDetalle.archivo_id == archivo.archivo_id)
            .order_by(ArchivoDetalle.archivo_detalle_id.asc())
            .all()
        )

        # 🔹 Débitos
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

        # 🔹 Motivos por lado (🔥 ahora vienen precargados)
        motivos_frente = (
            session.query(MotivoDebito)
            .filter(MotivoDebito.lado == "F")
            .order_by(MotivoDebito.motivo_debito_id.asc())
            .all()
        )

        motivos_dorso = (
            session.query(MotivoDebito)
            .filter(MotivoDebito.lado == "D")
            .order_by(MotivoDebito.motivo_debito_id.asc())
            .all()
        )

        # 🔹 Historial (🔥 MISMA sesión, no abrimos otra)
        has_historial = False
        if archivo and archivo.archivo_id:
            has_historial = HistorialRecetaService.has_historial_debitada(
                session,
                archivo_id=archivo.archivo_id
            )


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
        )
