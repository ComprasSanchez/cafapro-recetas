from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config.settings import settings

# DB_LEGACY — migrado a API en v4.0.0. Comentado para rollback si es necesario.
# from sqlalchemy import select, func, update
# from sqlalchemy.orm import Session
# from app.db.models import (
#     Recetas,
#     Asociacion,
#     Debitos,
#     MotivoDebito,
#     Usuarios,
#     Vendedores,
#     EstadoReceta,
#     Archivo,
#     Recepcion,
# )


@dataclass(frozen=True)
class CurrentSnapshotOut:
    frente_path: Optional[str]
    dorso_path: Optional[str]


class HistorialRecetaService:
    """
    Historial simple por archivo_id.
    - Snapshot: receta vigente asociada al archivo.
    - Historial: todas las recetas asociadas al archivo.
    - Débitos: por receta seleccionada.
    """

    # DB_LEGACY — comentado en v4.0.0, reemplazado por hasHistorialDebitada en el endpoint de auditoría
    # @staticmethod
    # def has_historial_debitada(s: Session, *, archivo_id: int) -> bool:
    #     q = (
    #         select(Recetas.receta_id)
    #         .join(Asociacion, Asociacion.receta_id == Recetas.receta_id)
    #         .where(
    #             Asociacion.archivo_id == int(archivo_id),
    #             Recetas.vigente.is_(False),
    #         )
    #         .limit(1)
    #     )
    #     return s.execute(q).scalar_one_or_none() is not None

    # -------------------------------------------------
    # Snapshot actual (solo imágenes)
    # -------------------------------------------------
    @staticmethod
    def load_current_snapshot(*, archivo_id: int) -> CurrentSnapshotOut:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/archivos/{int(archivo_id)}/historial-snapshot"
        resp = httpx.get(url, timeout=600)
        resp.raise_for_status()
        d = resp.json()
        return CurrentSnapshotOut(
            frente_path=d.get("frentePath"),
            dorso_path=d.get("dorsoPath"),
        )

    # -------------------------------------------------
    # Historial de auditorías
    # -------------------------------------------------
    @staticmethod
    def list_historial(*, archivo_id: int) -> list[dict]:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/archivos/{int(archivo_id)}/historial"
        resp = httpx.get(url, timeout=600)
        resp.raise_for_status()
        return [
            {
                "receta_id": int(r.get("recetaId") or 0),
                "vigente": bool(r.get("vigente", False)),
                "auditor_username": r.get("auditorUsername"),
                "estado_receta": r.get("estadoReceta"),
                "auditado_en": r.get("auditadoEn"),
                "cantidad_debitos": int(r.get("cantidadDebitos") or 0),
            }
            for r in resp.json()
        ]

    # -------------------------------------------------
    # Débitos por receta
    # -------------------------------------------------
    @staticmethod
    def list_debitos_for_receta(*, receta_id: int) -> list[dict]:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}/historial-detail"
        resp = httpx.get(url, timeout=600)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return [
            {
                "motivo": d.get("motivo") or "",
                "detalle": d.get("detalle") or "",
                "reportado_por": d.get("reportadoPor") or "",
                "vendedor": d.get("vendedor") or "",
                "marcado_en": d.get("marcadoEn") or "",
            }
            for d in resp.json().get("debitos", [])
        ]

    @staticmethod
    def get_imagenes_por_receta(*, receta_id: int) -> dict:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/recetas/{int(receta_id)}/historial-detail"
        resp = httpx.get(url, timeout=600)
        if resp.status_code == 404:
            return {"frente": None, "dorso": None}
        resp.raise_for_status()
        imgs = resp.json().get("imagenes", {})
        return {
            "frente": imgs.get("frente"),
            "dorso": imgs.get("dorso"),
        }

    @staticmethod
    def search_historial_by_numero_receta(*, nro_receta: str) -> list[dict]:
        return HistorialRecetaService._search_historial(nro_receta=str(nro_receta).strip())

    @staticmethod
    def search_historial_by_numero_referencia(*, nro_referencia: str) -> list[dict]:
        return HistorialRecetaService._search_historial(nro_referencia=str(nro_referencia).strip())

    @staticmethod
    def _search_historial(nro_receta: str | None = None, nro_referencia: str | None = None) -> list[dict]:
        url = f"{settings.API_CAFAPRO.rstrip('/')}/historial/buscar"
        params: dict = {}
        if nro_receta:
            params["nroReceta"] = nro_receta
        if nro_referencia:
            params["nroReferencia"] = nro_referencia
        resp = httpx.get(url, params=params, timeout=600)
        resp.raise_for_status()
        return [
            {
                "receta_id": int(r.get("recetaId") or 0),
                "vigente": bool(r.get("vigente", False)),
                "auditor_username": r.get("auditorUsername"),
                "estado_receta": r.get("estadoReceta"),
                "auditado_en": r.get("auditadoEn"),
                "cantidad_debitos": int(r.get("cantidadDebitos") or 0),
                "nro_receta": r.get("nroReceta"),
                "nro_referencia": r.get("nroReferencia"),
                "recepcion_numero": r.get("recepcionNumero"),
            }
            for r in resp.json()
        ]

    # DB_LEGACY — los tres métodos siguientes fueron migrados a POST /recepciones/:id/actualizar-historial en v4.0.0
    # @staticmethod
    # def actualizar_historial_recepcion(s: Session, recepcion_id: int) -> None: ...
    # @staticmethod
    # def actualizar_historial_receta(s: Session, *, receta_id, nro_referencia, nro_receta, recepcion_id) -> None: ...
    # @staticmethod
    # def restaurar_historial_receta(s: Session, *, nro_referencia, nro_receta, recepcion_id) -> None: ...
