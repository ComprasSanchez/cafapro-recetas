from __future__ import annotations

from sqlalchemy import select

from app.db.models import ObraSocial


OBRAS_SOCIALES = [
    {"codigo": "12", "nombre": "APROSS"},
    {"codigo": "80", "nombre": "PAMI"},
]


def run(session) -> None:
    for it in OBRAS_SOCIALES:
        codigo = (it["codigo"] or "").strip()
        nombre = (it["nombre"] or "").strip()

        if not codigo:
            continue

        obj = session.execute(
            select(ObraSocial).where(ObraSocial.codigo == codigo)
        ).scalar_one_or_none()

        if obj:
            obj.nombre = nombre
            obj.activo = True
            session.add(obj)
        else:
            session.add(ObraSocial(codigo=codigo, nombre=nombre, activo=True))

    session.commit()
