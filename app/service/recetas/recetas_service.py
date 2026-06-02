from __future__ import annotations

from datetime import date, datetime

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.models import Recetas, Asociacion, Troqueles, Archivo, Debitos


class RecetaService:
    ESTADO_SEGUIMIENTO_PROCESADA = 6
    ESTADO_RECETA_REVISION = 3

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
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}/estado-seguimiento"
        resp = httpx.patch(url, json={"estadoSeguimientoId": estado_seguimiento_id}, timeout=10)
        if resp.status_code == 404:
            raise ValueError(f"No existe receta_id={receta_id}")
        resp.raise_for_status()

    @staticmethod
    def anular_receta(receta_id: int, nro_receta: str) -> None:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}/anular"
        resp = httpx.patch(url, json={"nroReceta": str(nro_receta)}, timeout=10)
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        resp.raise_for_status()

    @staticmethod
    def duplicar_receta(receta_id: int, nro_receta: str) -> None:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}/duplicar"
        resp = httpx.patch(url, json={"nroReceta": str(nro_receta)}, timeout=10)
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        resp.raise_for_status()

    @staticmethod
    def eliminar_sobrante(*, receta_id: int) -> None:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}"
        resp = httpx.delete(url, timeout=15)
        if resp.status_code == 404:
            raise RuntimeError("Receta no encontrada")
        if resp.status_code == 400:
            raise RuntimeError(resp.json().get("message", "Solo se pueden eliminar recetas en revisión"))
        resp.raise_for_status()

    @staticmethod
    def eliminar_sobrantes_bulk(*, receta_ids: list[int]) -> dict:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/bulk"
        ids = list({int(r) for r in (receta_ids or []) if int(r or 0) > 0})
        resp = httpx.request("DELETE", url, json={"recetaIds": ids}, timeout=30)
        resp.raise_for_status()
        return resp.json()



