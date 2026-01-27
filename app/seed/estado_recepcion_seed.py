from __future__ import annotations

from sqlalchemy import select

from app.db.models import EstadoReceta


def run(session) -> None:
    estado_recepcion = ["ABIERTO", "CERRADO"]

    for descripcion in estado_recepcion:
        exists = session.execute(
            select(EstadoReceta).where(EstadoReceta.descripcion == descripcion)
        ).scalar_one_or_none()

        if not exists:
            session.add(EstadoReceta(descripcion=descripcion))

    session.commit()