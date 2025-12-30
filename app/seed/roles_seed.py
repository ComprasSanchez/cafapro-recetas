from __future__ import annotations

from sqlalchemy import select
from app.db.models import Roles


def run(session) -> None:
    roles = ["ADMIN", "AUDITOR"]

    for descripcion in roles:
        exists = session.execute(
            select(Roles).where(Roles.descripcion == descripcion)
        ).scalar_one_or_none()

        if not exists:
            session.add(Roles(descripcion=descripcion))
