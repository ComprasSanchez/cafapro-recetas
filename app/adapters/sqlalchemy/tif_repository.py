from __future__ import annotations

from typing import cast

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.db.models import Archivo, ArchivoDetalle, Asociacion, Debitos, ObraSocial, Prestador, Recepcion, Recetas


class TifRepository:
    @staticmethod
    def exists_processed_base_in_recepcion(session: Session, *, recepcion_id: int, base_name: str) -> bool:
        like_pat = f"%/{base_name}_%"
        rid = (
            session.execute(
                select(Recetas.receta_id)
                .where(
                    and_(
                        Recetas.recepcion_id == int(recepcion_id),
                        or_(
                            Recetas.ubicacion_frente.ilike(like_pat),
                            Recetas.ubicacion_dorso.ilike(like_pat),
                        ),
                    )
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return rid is not None

    @staticmethod
    def list_archivos_for_match(
        session: Session,
        *,
        recepcion_id: int,
        candidate_values: list[str],
        only_referencia: bool,
    ) -> list[Archivo]:
        where_match = Archivo.nro_referencia.in_(candidate_values)
        if not only_referencia:
            where_match = or_(
                where_match,
                Archivo.nro_receta.in_(candidate_values),
            )

        return cast(list[Archivo], list(
            session.execute(
                select(Archivo).where(
                    and_(
                        Archivo.recepcion_id == int(recepcion_id),
                        where_match,
                    )
                )
            )
            .scalars()
        ))

    @staticmethod
    def is_archivo_ya_asociado(session: Session, *, recepcion_id: int, archivo_id: int) -> bool:
        rid = (
            session.execute(
                select(Recetas.receta_id)
                .join(Asociacion, Asociacion.receta_id == Recetas.receta_id)
                .where(
                    Recetas.recepcion_id == int(recepcion_id),
                    Asociacion.archivo_id == int(archivo_id),
                    Asociacion.vigente.is_(True),
                )
                .limit(1)
            )
            .scalar_one_or_none()
        )
        return rid is not None

    @staticmethod
    def list_archivo_ids_ya_asociados(
        session: Session,
        *,
        recepcion_id: int,
        archivo_ids: list[int],
    ) -> set[int]:
        if not archivo_ids:
            return set()

        rows = session.execute(
            select(Asociacion.archivo_id)
            .join(Recetas, Recetas.receta_id == Asociacion.receta_id)
            .where(
                Recetas.recepcion_id == int(recepcion_id),
                Asociacion.archivo_id.in_(archivo_ids),
                Asociacion.vigente.is_(True),
            )
        ).scalars().all()

        return {int(x) for x in rows if x is not None}

    @staticmethod
    def get_recepcion(session: Session, *, recepcion_id: int) -> Recepcion | None:
        return session.execute(
            select(Recepcion).where(Recepcion.recepcion_id == int(recepcion_id))
        ).scalar_one_or_none()

    @staticmethod
    def get_prestador(session: Session, *, prestador_id: int) -> Prestador | None:
        return session.execute(
            select(Prestador).where(Prestador.prestador_id == int(prestador_id))
        ).scalar_one_or_none()

    @staticmethod
    def get_obra_social_context(session: Session, *, obra_social_id: int):
        return session.execute(
            select(ObraSocial.nombre, ObraSocial.dias_vencimiento)
            .where(ObraSocial.obra_social_id == int(obra_social_id))
        ).first()

    @staticmethod
    def get_archivos_by_ids(session: Session, *, archivo_ids: list[int]) -> list[Archivo]:
        if not archivo_ids:
            return []
        return cast(list[Archivo], list(session.execute(
            select(Archivo).where(Archivo.archivo_id.in_(archivo_ids))
        ).scalars().all()))

    @staticmethod
    def get_detalles_by_archivo_ids(session: Session, *, archivo_ids: list[int]) -> list[ArchivoDetalle]:
        if not archivo_ids:
            return []
        return cast(list[ArchivoDetalle], list(session.execute(
            select(ArchivoDetalle).where(ArchivoDetalle.archivo_id.in_(archivo_ids))
        ).scalars().all()))

    @staticmethod
    def load_archivo_bundle(
        session: Session,
        *,
        archivo_ids: list[int],
    ) -> tuple[dict[int, Archivo], dict[int, list[ArchivoDetalle]]]:
        if not archivo_ids:
            return {}, {}

        archivos = session.execute(
            select(Archivo).where(Archivo.archivo_id.in_(archivo_ids))
        ).scalars().all()
        archivo_by_id = {a.archivo_id: a for a in archivos}

        detalles = session.execute(
            select(ArchivoDetalle).where(ArchivoDetalle.archivo_id.in_(archivo_ids))
        ).scalars().all()

        detalles_by_archivo: dict[int, list[ArchivoDetalle]] = {}
        for d in detalles:
            detalles_by_archivo.setdefault(d.archivo_id, []).append(d)

        return archivo_by_id, detalles_by_archivo

    @staticmethod
    def get_recetas_with_motivo(
        session: Session,
        *,
        receta_ids: list[int],
        motivo_id: int,
    ) -> set[int]:
        if not receta_ids:
            return set()
        return set(
            session.execute(
                select(Debitos.receta_id).where(
                    Debitos.motivo_debito_id == int(motivo_id),
                    Debitos.receta_id.in_(receta_ids),
                )
            ).scalars().all()
        )
