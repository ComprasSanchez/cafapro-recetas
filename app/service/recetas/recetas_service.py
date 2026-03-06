from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Recetas, Asociacion, Troqueles, Archivo, Debitos
from app.db.session import session_scope
from app.infra.storage import s3_storage


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
        receta = (
            s.execute(
                select(Recetas)
                .where(
                    Recetas.recepcion_id == int(recepcion_id),
                    Recetas.nro_receta == str(nro_receta),
                    Recetas.vigente.is_(True),
                )
                .limit(1)
            )
            .scalars()
            .first()
        )

        if not receta:
            receta = Recetas(
                recepcion_id=int(recepcion_id),
                nro_receta=str(nro_receta),
                ubicacion_frente=ubicacion_frente,
                ubicacion_dorso=ubicacion_dorso,
                fecha_prescripcion=None,
                estado_seguimiento_id=self.ESTADO_SEGUIMIENTO_PROCESADA,
                observacion=None,
                usuario_id=usuario_id,  # si tu DB lo permite None, ok
                vigente=True,
            )
            s.add(receta)
            s.flush()
        else:
            # actualizo SOLO la vigente
            receta.estado_seguimiento_id = self.ESTADO_SEGUIMIENTO_PROCESADA
            receta.ubicacion_frente = ubicacion_frente
            receta.ubicacion_dorso = ubicacion_dorso

        return receta

    @staticmethod
    def ensure_asociacion(s: Session, receta_id: int, archivo_id: int) -> bool:
        existe = (
            s.execute(
                select(Asociacion)
                .where(
                    Asociacion.receta_id == int(receta_id),
                    Asociacion.archivo_id == int(archivo_id),
                )
                .limit(1)
            )
            .scalars()
            .first()
        )

        if existe:
            return False

        s.add(Asociacion(receta_id=int(receta_id), archivo_id=int(archivo_id), vigente=True))
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
                    receta_id=int(receta_id),
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
        archivo.recepcion_id = int(recepcion_id)

    @staticmethod
    def update_auditoria(
            session: Session,
            receta_id: int,
            vendedor_id: int | None,
            estado_seguimiento_id: int | None,
            fecha_prescripcion: date | None,
            fecha_emision: date,
            fecha_venta: date,
            estado_receta_id: int = 1,
            usuario_id: int | None = None,
    ) -> None:
        r = session.get(Recetas, int(receta_id))
        if not r:
            raise ValueError(f"Receta {receta_id} no existe")

        r.vendedor_id = vendedor_id
        r.estado_seguimiento_id = estado_seguimiento_id
        r.estado_receta_id = int(estado_receta_id)

        # Prescripción: editable pero NO obligatoria
        r.fecha_prescripcion = fecha_prescripcion

        # Nuevas: obligatorias por validación del dialog
        r.fecha_emision = fecha_emision
        r.fecha_venta = fecha_venta

        r.usuario_id = usuario_id
        r.creado_en = datetime.now()

    @staticmethod
    def update_estado_seguimiento(receta_id: int, estado_seguimiento_id: int | None) -> None:
        """Actualiza el estado de seguimiento en la receta."""
        with session_scope() as s:
            rec = (
                s.query(Recetas)
                .filter(Recetas.receta_id == int(receta_id))
                .one_or_none()
            )
            if rec is None:
                raise ValueError(f"No existe receta_id={receta_id}")

            rec.estado_seguimiento_id = estado_seguimiento_id

    @staticmethod
    def anular_receta(s: Session, receta_id: int, nro_receta: str):

        receta = s.get(Recetas, receta_id)

        if not receta:
            raise RuntimeError("Receta no encontrada")

        # actualizar numero receta
        receta.nro_receta = nro_receta

        # estado ANULADA
        receta.estado_receta_id = 4

        # evitar duplicar debito
        existe = s.execute(
            select(Debitos.debito_id)
            .where(
                Debitos.receta_id == receta_id,
                Debitos.motivo_debito_id == 24
            )
        ).first()

        if not existe:
            deb = Debitos(
                receta_id=receta_id,
                motivo_debito_id=24,
                detalle="Receta Anulada"
            )
            s.add(deb)

    @staticmethod
    def duplicar_receta(s: Session, receta_id: int, nro_receta: str):

        receta = s.get(Recetas, receta_id)

        if not receta:
            raise RuntimeError("Receta no encontrada")

        # actualizar numero receta
        receta.nro_receta = nro_receta

        # estado DUPLICADA
        receta.estado_receta_id = 5

        # evitar duplicar debito
        existe = s.execute(
            select(Debitos.debito_id)
            .where(
                Debitos.receta_id == receta_id,
                Debitos.motivo_debito_id == 32,
            )
        ).first()

        if not existe:
            deb = Debitos(
                receta_id=receta_id,
                motivo_debito_id=32,
                detalle="RECETA DUPLICADA",
            )
            s.add(deb)

    @staticmethod
    def eliminar_sobrante(
            s: Session,
            *,
            receta_id: int,
    ) -> None:

        receta = s.get(Recetas, receta_id)

        if not receta:
            raise RuntimeError("Receta no encontrada")

        # ---------------------------------
        # eliminar imágenes S3
        # ---------------------------------

        if receta.ubicacion_frente:
            s3_storage.delete_object(receta.ubicacion_frente)

        if receta.ubicacion_dorso:
            s3_storage.delete_object(receta.ubicacion_dorso)

        # ---------------------------------
        # eliminar receta
        # ---------------------------------

        s.delete(receta)



