from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ObraSocial


# =========================
# DTOs
# =========================
@dataclass(frozen=True)
class ObraSocialItem:
    obra_social_id: int
    codigo: str
    nombre: str
    activo: bool


# =========================
# SERVICE
# =========================
class ObraSocialService:

    # ---------------------
    # LISTADOS
    # ---------------------
    @staticmethod
    def list(s: Session, *, solo_activas: bool = True) -> list[ObraSocialItem]:
        stmt = select(
            ObraSocial.obra_social_id,
            ObraSocial.codigo,
            ObraSocial.nombre,
            ObraSocial.activo,
        )

        if solo_activas:
            stmt = stmt.where(ObraSocial.activo.is_(True))

        stmt = stmt.order_by(ObraSocial.nombre)

        rows = s.execute(stmt).all()

        return [
            ObraSocialItem(
                obra_social_id=r[0],
                codigo=r[1],
                nombre=r[2],
                activo=r[3],
            )
            for r in rows
        ]

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(s: Session, obra_social_id: int) -> ObraSocial | None:
        return s.get(ObraSocial, obra_social_id)

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        s: Session,
        *,
        codigo: str,
        nombre: str,
    ) -> ObraSocial:
        codigo = codigo.strip()
        nombre = nombre.strip()

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios")

        existe = s.execute(
            select(ObraSocial).where(ObraSocial.codigo == codigo)
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe una obra social con código '{codigo}'")

        os = ObraSocial(
            codigo=codigo,
            nombre=nombre,
            activo=True,
        )

        s.add(os)
        s.flush()      # para obtener obra_social_id
        s.refresh(os)

        return os

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        s: Session,
        *,
        obra_social_id: int,
        codigo: str,
        nombre: str,
    ) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        codigo = codigo.strip()
        nombre = nombre.strip()

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios")

        # validar código único (excluyendo la actual)
        existe = s.execute(
            select(ObraSocial)
            .where(
                ObraSocial.codigo == codigo,
                ObraSocial.obra_social_id != obra_social_id,
            )
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe otra obra social con código '{codigo}'")

        os.codigo = codigo
        os.nombre = nombre

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(s: Session, obra_social_id: int) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        os.activo = False

    # ---------------------
    # RESTAURAR
    # ---------------------
    @staticmethod
    def restore(s: Session, obra_social_id: int) -> None:
        os = s.get(ObraSocial, obra_social_id)
        if not os:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")

        os.activo = True
