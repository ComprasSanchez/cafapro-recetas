from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Prestador


@dataclass(frozen=True)
class PrestadorItem:
    prestador_id: int
    nombre: str
    codigo: str
    imed: str
    activo: bool


class PrestadorService:
    # ---------------------
    # LIST
    # ---------------------
    @staticmethod
    def list(s: Session, *, solo_activos: bool = False) -> list[PrestadorItem]:
        stmt = select(
            Prestador.prestador_id,
            Prestador.nombre,
            Prestador.codigo,
            Prestador.imed,
            Prestador.activo,
        )

        if solo_activos:
            stmt = stmt.where(Prestador.activo.is_(True))

        stmt = stmt.order_by(Prestador.nombre.nulls_last(), Prestador.codigo)

        rows = s.execute(stmt).all()
        return [
            PrestadorItem(
                prestador_id=r[0],
                nombre=r[1] or "(sin nombre)",
                codigo=r[2] or "",
                imed=r[3] or "",
                activo=bool(r[4]),
            )
            for r in rows
        ]

    # ---------------------
    # GET
    # ---------------------
    @staticmethod
    def get(s: Session, prestador_id: int) -> Prestador | None:
        return s.get(Prestador, int(prestador_id))

    # ---------------------
    # CREATE
    # ---------------------
    @staticmethod
    def create(
        s: Session,
        *,
        codigo: str,
        nombre: str | None = None,
        imed: str | None = None,
    ) -> Prestador:
        codigo = (codigo or "").strip()
        nombre = (nombre or "").strip() if nombre is not None else None
        imed = (imed or "").strip() if imed is not None else None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        # codigo único
        existe = s.execute(
            select(Prestador.prestador_id).where(Prestador.codigo == codigo).limit(1)
        ).scalar_one_or_none()
        if existe:
            raise ValueError(f"Ya existe un prestador con código '{codigo}'.")

        p = Prestador(
            codigo=codigo,
            nombre=nombre,
            imed=imed,
            activo=True,
        )
        s.add(p)

        try:
            s.flush()
            s.refresh(p)
        except IntegrityError as e:
            raise ValueError("No se pudo crear el prestador (código duplicado).") from e

        return p

    # ---------------------
    # UPDATE
    # ---------------------
    @staticmethod
    def update(
        s: Session,
        *,
        prestador_id: int,
        codigo: str,
        nombre: str | None = None,
        imed: str | None = None,
    ) -> None:
        p = s.get(Prestador, int(prestador_id))
        if not p:
            raise ValueError(f"No existe prestador_id={prestador_id}")

        codigo = (codigo or "").strip()
        nombre = (nombre or "").strip() if nombre is not None else None
        imed = (imed or "").strip() if imed is not None else None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        # validar código único excluyendo el mismo
        existe = s.execute(
            select(Prestador.prestador_id)
            .where(
                Prestador.codigo == codigo,
                Prestador.prestador_id != int(prestador_id),
            )
            .limit(1)
        ).scalar_one_or_none()

        if existe:
            raise ValueError(f"Ya existe otro prestador con código '{codigo}'.")

        p.codigo = codigo
        p.nombre = nombre
        p.imed = imed

        try:
            s.flush()
        except IntegrityError as e:
            raise ValueError("No se pudo actualizar el prestador (código duplicado).") from e

    # ---------------------
    # BAJA LÓGICA
    # ---------------------
    @staticmethod
    def delete_logico(s: Session, prestador_id: int) -> None:
        p = s.get(Prestador, int(prestador_id))
        if not p:
            raise ValueError(f"No existe prestador_id={prestador_id}")

        p.activo = False

    # ---------------------
    # RESTORE
    # ---------------------
    @staticmethod
    def restore(s: Session, prestador_id: int) -> None:
        p = s.get(Prestador, int(prestador_id))
        if not p:
            raise ValueError(f"No existe prestador_id={prestador_id}")

        p.activo = True

