from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Vendedores


# =========================
# DTO
# =========================
@dataclass(frozen=True)
class VendedorItem:
    vendedor_id: int
    codigo: str
    descripcion: str
    activo: bool


# =========================
# SERVICE
# =========================
class VendedoresService:
    # ---------------------
    # LIST
    # ---------------------
    @staticmethod
    def list(session: Session, *, solo_activos: bool = False) -> list[VendedorItem]:
        stmt = select(
            Vendedores.vendedor_id,
            Vendedores.codigo,
            Vendedores.descripcion,
            Vendedores.activo,
        )

        if solo_activos:
            stmt = stmt.where(Vendedores.activo.is_(True))

        stmt = stmt.order_by(Vendedores.descripcion.asc())

        rows = session.execute(stmt).all()
        return [
            VendedorItem(
                vendedor_id=r[0],
                codigo=r[1],
                descripcion=r[2],
                activo=bool(r[3]),
            )
            for r in rows
        ]

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(session: Session, vendedor_id: int) -> Vendedores | None:
        return session.get(Vendedores, int(vendedor_id))

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        session: Session,
        *,
        codigo: str,
        descripcion: str,
    ) -> Vendedores:
        codigo = (codigo or "").strip()
        descripcion = (descripcion or "").strip()

        if not codigo:
            raise ValueError("El código es obligatorio.")
        if not descripcion:
            raise ValueError("La descripción es obligatoria.")

        existe = session.execute(
            select(Vendedores.vendedor_id)
            .where(Vendedores.codigo == codigo)
            .limit(1)
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe un vendedor con código '{codigo}'.")

        v = Vendedores(
            codigo=codigo,
            descripcion=descripcion,
            activo=True,
        )
        session.add(v)

        try:
            session.flush()
            session.refresh(v)
        except IntegrityError as e:
            raise ValueError("No se pudo crear el vendedor (código duplicado).") from e

        return v

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        session: Session,
        *,
        vendedor_id: int,
        codigo: str,
        descripcion: str,
    ) -> None:
        v = session.get(Vendedores, int(vendedor_id))
        if not v:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")

        codigo = (codigo or "").strip()
        descripcion = (descripcion or "").strip()

        if not codigo:
            raise ValueError("El código es obligatorio.")
        if not descripcion:
            raise ValueError("La descripción es obligatoria.")

        existe = session.execute(
            select(Vendedores.vendedor_id)
            .where(
                Vendedores.codigo == codigo,
                Vendedores.vendedor_id != int(vendedor_id),
            )
            .limit(1)
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe otro vendedor con código '{codigo}'.")

        v.codigo = codigo
        v.descripcion = descripcion

        try:
            session.flush()
        except IntegrityError as e:
            raise ValueError("No se pudo actualizar el vendedor.") from e

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(session: Session, vendedor_id: int) -> None:
        v = session.get(Vendedores, int(vendedor_id))
        if not v:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")

        v.activo = False

    # ---------------------
    # RESTORE
    # ---------------------
    @staticmethod
    def restore(session: Session, vendedor_id: int) -> None:
        v = session.get(Vendedores, int(vendedor_id))
        if not v:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")

        v.activo = True

