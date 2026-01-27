from __future__ import annotations

from sqlalchemy import select

from app.db.models import EstadoRecepcion


def run(session) -> None:
    estado_recepcion = ["Auditada", "No Auditada"]

    for descripcion in estado_recepcion:
        exists = session.execute(
            select(EstadoRecepcion).where(EstadoRecepcion.descripcion == descripcion)
        ).scalar_one_or_none()

        if not exists:
            session.add(EstadoRecepcion(descripcion=descripcion))

    session.commit()
