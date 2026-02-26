from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.models import (
    Recetas,
    Asociacion,
    Debitos,
    MotivoDebito,
    Usuarios,
    EstadoReceta,
)


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

    @staticmethod
    def has_historial_debitada(s: Session, *, archivo_id: int) -> bool:
        q = (
            select(Recetas.receta_id)
            .join(Asociacion, Asociacion.receta_id == Recetas.receta_id)
            .where(
                Asociacion.archivo_id == int(archivo_id),
                Recetas.vigente.is_(False),
            )
            .limit(1)
        )

        return s.execute(q).scalar_one_or_none() is not None

    # -------------------------------------------------
    # Snapshot actual (solo imágenes)
    # -------------------------------------------------
    @staticmethod
    def load_current_snapshot(s: Session, *, archivo_id: int) -> CurrentSnapshotOut:
        rec = (
            s.execute(
                select(Recetas)
                .join(Asociacion, Asociacion.receta_id == Recetas.receta_id)
                .where(
                    Asociacion.archivo_id == int(archivo_id),
                    Asociacion.vigente.is_(True),
                    Recetas.vigente.is_(True),
                )
                .order_by(Recetas.receta_id.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

        frente = (rec.ubicacion_frente or "").strip() if rec else None
        dorso = (rec.ubicacion_dorso or "").strip() if rec else None

        return CurrentSnapshotOut(frente_path=frente, dorso_path=dorso)

    # -------------------------------------------------
    # Historial de auditorías
    # -------------------------------------------------
    @staticmethod
    def list_historial(s: Session, *, archivo_id: int) -> list[dict]:
        q = (
            select(
                Recetas.receta_id.label("receta_id"),
                Recetas.vigente.label("vigente"),
                Usuarios.username.label("auditor_username"),
                EstadoReceta.descripcion.label("estado_receta"),
                Recetas.creado_en.label("auditado_en"),
                func.count(Debitos.debito_id).label("cantidad_debitos"),
            )
            .select_from(Asociacion)
            .join(Recetas, Recetas.receta_id == Asociacion.receta_id)
            .outerjoin(Debitos, Debitos.receta_id == Recetas.receta_id)
            .outerjoin(Usuarios, Usuarios.usuario_id == Recetas.usuario_id)
            .outerjoin(
                EstadoReceta,
                EstadoReceta.estado_receta_id == Recetas.estado_receta_id,
            )
            .where(Asociacion.archivo_id == int(archivo_id))
            .group_by(
                Recetas.receta_id,
                Recetas.vigente,
                Usuarios.username,
                EstadoReceta.descripcion,
                Recetas.creado_en,
            )
            .order_by(Recetas.vigente.desc(), Recetas.receta_id.desc())
        )

        rows = []
        for r in s.execute(q).mappings().all():
            fecha = r["auditado_en"]
            fecha_txt = (
                fecha.strftime("%d/%m/%Y %H:%M") if fecha else None
            )

            rows.append(
                {
                    "receta_id": int(r["receta_id"]),
                    "vigente": bool(r["vigente"]),
                    "auditor_username": r["auditor_username"],
                    "estado_receta": r["estado_receta"],
                    "auditado_en": fecha_txt,
                    "cantidad_debitos": int(r["cantidad_debitos"] or 0),
                }
            )

        return rows

    # -------------------------------------------------
    # Débitos por receta
    # -------------------------------------------------
    @staticmethod
    def list_debitos_for_receta(s: Session, *, receta_id: int) -> list[dict]:
        q = (
            select(
                MotivoDebito.descripcion.label("motivo"),
                Debitos.detalle.label("detalle"),
            )
            .select_from(Debitos)
            .join(
                MotivoDebito,
                MotivoDebito.motivo_debito_id == Debitos.motivo_debito_id,
            )
            .where(Debitos.receta_id == int(receta_id))
            .order_by(MotivoDebito.descripcion.asc())
        )

        return [
            {
                "motivo": r["motivo"] or "",
                "detalle": r["detalle"] or "",
            }
            for r in s.execute(q).mappings().all()
        ]

    # -------------------------------------------------
    # Cargar imágenes por receta
    # -------------------------------------------------
    @staticmethod
    def get_imagenes_por_receta(s: Session, *, receta_id: int) -> dict:
        rec = s.get(Recetas, int(receta_id))
        if not rec:
            return {"frente": None, "dorso": None}

        return {
            "frente": (rec.ubicacion_frente or "").strip() or None,
            "dorso": (rec.ubicacion_dorso or "").strip() or None,
        }