from __future__ import annotations

from sqlalchemy import select

from app.db.models import EstadoSeguimiento


def run(session) -> None:
    roles = ["Enviado corregida", "Enviada sin corregir", "No enviada", "Escaneada", "Auditada"]

    for descripcion in roles:
        exists = session.execute(
            select(EstadoSeguimiento).where(EstadoSeguimiento.descripcion == descripcion)
        ).scalar_one_or_none()

        if not exists:
            session.add(EstadoSeguimiento(descripcion=descripcion))
