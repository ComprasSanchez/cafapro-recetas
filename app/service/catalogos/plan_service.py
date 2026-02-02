from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Plan, ObraSocial


# =========================
# DTO
# =========================
@dataclass(frozen=True)
class PlanItem:
    plan_id: int
    obra_social_id: int
    obra_social: str
    codigo: Optional[str]
    nombre: Optional[str]
    activo: bool


# =========================
# SERVICE
# =========================
class PlanService:
    # ---------------------
    # Helpers
    # ---------------------
    @staticmethod
    def _norm_optional_str(x: Optional[str]) -> Optional[str]:
        if x is None:
            return None
        x = str(x).strip()
        return x if x else None

    @staticmethod
    def _exists_combo(
        session: Session,
        *,
        obra_social_id: int,
        nombre: Optional[str],
        codigo: Optional[str],
        exclude_plan_id: int | None = None,
    ) -> bool:
        """
        Valida el unique lógico: (obra_social_id, nombre, codigo)
        - Normaliza strings (None / strip).
        - Excluye un plan_id en caso de update.
        """
        nombre = PlanService._norm_optional_str(nombre)
        codigo = PlanService._norm_optional_str(codigo)

        stmt = select(Plan.plan_id).where(
            and_(
                Plan.obra_social_id == int(obra_social_id),
                Plan.nombre.is_(None) if nombre is None else Plan.nombre == nombre,
                Plan.codigo.is_(None) if codigo is None else Plan.codigo == codigo,
            )
        )

        if exclude_plan_id is not None:
            stmt = stmt.where(Plan.plan_id != int(exclude_plan_id))

        return session.execute(stmt.limit(1)).scalar_one_or_none() is not None

    # ---------------------
    # LIST
    # ---------------------
    @staticmethod
    def list(session: Session, *, solo_activos: bool = True) -> list[PlanItem]:
        stmt = (
            select(
                Plan.plan_id,
                Plan.obra_social_id,
                ObraSocial.nombre,
                Plan.codigo,
                Plan.nombre,
                Plan.activo,
            )
            .join(ObraSocial, ObraSocial.obra_social_id == Plan.obra_social_id)
        )

        if solo_activos:
            stmt = stmt.where(Plan.activo.is_(True))

        stmt = stmt.order_by(ObraSocial.nombre.asc(), Plan.nombre.nulls_last(), Plan.codigo.nulls_last(), Plan.plan_id.desc())

        rows = session.execute(stmt).all()

        out: list[PlanItem] = []
        for plan_id, obra_social_id, os_nombre, codigo, nombre, activo in rows:
            out.append(
                PlanItem(
                    plan_id=int(plan_id),
                    obra_social_id=int(obra_social_id),
                    obra_social=os_nombre or "",
                    codigo=codigo,
                    nombre=nombre,
                    activo=bool(activo),
                )
            )
        return out

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(session: Session, plan_id: int) -> Plan | None:
        return session.get(Plan, int(plan_id))

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        session: Session,
        *,
        obra_social_id: int,
        codigo: str | None = None,
        nombre: str | None = None,
    ) -> Plan:
        obra_social_id = int(obra_social_id)
        codigo = PlanService._norm_optional_str(codigo)
        nombre = PlanService._norm_optional_str(nombre)

        # si querés obligar a que al menos uno venga informado:
        # if not codigo and not nombre:
        #     raise ValueError("Debés ingresar código o nombre (al menos uno).")

        if PlanService._exists_combo(session, obra_social_id=obra_social_id, nombre=nombre, codigo=codigo):
            raise ValueError("Ya existe un plan con esa Obra Social + Nombre + Código.")

        p = Plan(
            obra_social_id=obra_social_id,
            codigo=codigo,
            nombre=nombre,
            activo=True,
        )
        session.add(p)

        try:
            session.flush()
            session.refresh(p)
        except IntegrityError as e:
            raise ValueError("No se pudo crear el plan (restricción UNIQUE).") from e

        return p

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        session: Session,
        *,
        plan_id: int,
        obra_social_id: int,
        codigo: str | None = None,
        nombre: str | None = None,
    ) -> None:
        plan_id = int(plan_id)
        obra_social_id = int(obra_social_id)
        codigo = PlanService._norm_optional_str(codigo)
        nombre = PlanService._norm_optional_str(nombre)

        p = session.get(Plan, plan_id)
        if not p:
            raise ValueError(f"No existe plan_id={plan_id}")

        if PlanService._exists_combo(
            session,
            obra_social_id=obra_social_id,
            nombre=nombre,
            codigo=codigo,
            exclude_plan_id=plan_id,
        ):
            raise ValueError("Ya existe otro plan con esa Obra Social + Nombre + Código.")

        p.obra_social_id = obra_social_id
        p.codigo = codigo
        p.nombre = nombre

        try:
            session.flush()
        except IntegrityError as e:
            raise ValueError("No se pudo actualizar el plan (restricción UNIQUE).") from e

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(session: Session, plan_id: int) -> None:
        p = session.get(Plan, int(plan_id))
        if not p:
            raise ValueError(f"No existe plan_id={plan_id}")
        p.activo = False

    # ---------------------
    # RESTORE
    # ---------------------
    @staticmethod
    def restore(session: Session, plan_id: int) -> None:
        p = session.get(Plan, int(plan_id))
        if not p:
            raise ValueError(f"No existe plan_id={plan_id}")
        p.activo = True
