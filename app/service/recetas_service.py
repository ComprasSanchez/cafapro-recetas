from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Recetas, Asociacion, Troqueles, Archivo


class RecetaService:
    ESTADO_SEGUIMIENTO_PROCESADA = 6

    def get_or_create_receta(
        self,
        s: Session,
        recepcion_id: int,
        nro_receta: str,
        usuario_id: int | None,
        ubicacion_frente: str | None,
        ubicacion_dorso: str | None,
    ) -> Recetas:
        receta = s.execute(
            select(Recetas).where(
                Recetas.recepcion_id == recepcion_id,
                Recetas.nro_receta == nro_receta,
            ).limit(1)
        ).scalars().first()

        if not receta:
            receta = Recetas(
                recepcion_id=recepcion_id,
                nro_receta=nro_receta,
                ubicacion_frente=ubicacion_frente,
                ubicacion_dorso=ubicacion_dorso,
                fecha_prescripcion=None,
                estado_seguimiento_id=self.ESTADO_SEGUIMIENTO_PROCESADA,
                observacion=None,
                usuario_id=usuario_id,  # puede ser None si tu DB lo permite
            )
            s.add(receta)
            s.flush()
        else:
            receta.estado_seguimiento_id = self.ESTADO_SEGUIMIENTO_PROCESADA
            receta.ubicacion_frente = ubicacion_frente
            receta.ubicacion_dorso = ubicacion_dorso

        return receta

    @staticmethod
    def ensure_asociacion(s: Session, receta_id: int, archivo_id: int) -> bool:
        """Devuelve True si creó la asociación, False si ya existía."""
        existe = s.execute(
            select(Asociacion).where(
                Asociacion.receta_id == receta_id,
                Asociacion.archivo_id == archivo_id,
            ).limit(1)
        ).scalars().first()

        if existe:
            return False

        s.add(Asociacion(receta_id=receta_id, archivo_id=archivo_id))
        return True

    @staticmethod
    def add_troqueles(s: Session, receta_id: int, troqueles: list[str]) -> int:
        """Inserta troqueles. Devuelve cuántos insertó."""
        inserted = 0
        for codigo in troqueles:
            codigo = str(codigo).strip()
            if not codigo:
                continue
            s.add(
                Troqueles(
                    receta_id=receta_id,
                    codigo_barra=codigo,
                    monto=0,       # placeholder por ahora
                    cantidad=1,    # placeholder
                    estado="OK",   # placeholder
                )
            )
            inserted += 1
        return inserted

    @staticmethod
    def attach_archivo_to_recepcion(archivo: Archivo, recepcion_id: int) -> None:
        archivo.recepcion_id = recepcion_id
