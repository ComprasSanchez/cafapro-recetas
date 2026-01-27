from sqlalchemy import select, func
from app.db.models import Roles

def run(session) -> None:
    roles = ["ADMIN", "AUDITOR"]
    for descripcion in roles:
        exists = session.execute(
            select(Roles).where(Roles.descripcion == descripcion)
        ).scalar_one_or_none()

        if not exists:
            session.add(Roles(descripcion=descripcion))

    session.commit()
