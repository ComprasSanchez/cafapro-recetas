from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import Archivo, Recetas, Asociacion
from app.service.recetas.historial_receta_service import HistorialRecetaService


class AsociacionService:

    @staticmethod
    def ejecutar(
            s: Session,
            *,
            receta_id: int,
            archivo_id: int,
    ) -> None:

        archivo = s.get(Archivo, archivo_id)
        if not archivo:
            raise RuntimeError("Archivo no encontrado")

        receta = s.get(Recetas, receta_id)
        if not receta:
            raise RuntimeError("Receta no encontrada")

        # ------------------------------------------------
        # 1) buscar asociación vigente del archivo
        # ------------------------------------------------
        asoc_prev = (
            s.execute(
                select(Asociacion)
                .where(
                    Asociacion.archivo_id == archivo_id,
                    Asociacion.vigente.is_(True),
                )
            )
            .scalar_one_or_none()
        )

        # ------------------------------------------------
        # 2) cerrar historial si existe
        # ------------------------------------------------
        if asoc_prev:
            s.execute(
                update(Asociacion)
                .where(
                    Asociacion.asociacion_id == asoc_prev.asociacion_id
                )
                .values(vigente=False)
            )

            s.execute(
                update(Recetas)
                .where(
                    Recetas.receta_id == asoc_prev.receta_id
                )
                .values(vigente=False)
            )

        # ------------------------------------------------
        # 3) actualizar receta actual
        # ------------------------------------------------
        receta.nro_receta = archivo.nro_receta
        receta.estado_receta_id = 2

        # ------------------------------------------------
        # 4) crear nueva asociación
        # ------------------------------------------------
        nueva = Asociacion(
            receta_id=receta.receta_id,
            archivo_id=archivo_id,
            vigente=True,
        )

        HistorialRecetaService.actualizar_historial_receta(
            s,
            receta_id=receta.receta_id,
            nro_referencia=archivo.nro_referencia,
            nro_receta=archivo.nro_receta,
            recepcion_id=receta.recepcion_id,
        )

        s.add(nueva)

        s.flush()