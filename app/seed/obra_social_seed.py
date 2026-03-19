from __future__ import annotations

from sqlalchemy import select

from app.db.models import ObraSocial


OBRAS_SOCIALES = [
    {"codigo": "12", "nombre": "APROSS", "codigo_financiador": 41},
    {"codigo": "80", "nombre": "PAMI", "codigo_financiador": 4007},
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
            obj.validador = "imed"
            obj.dias_vencimiento = 60
            obj.codigo_financiador = it.get("codigo_financiador")
            obj.activo = True
            session.add(obj)
        else:
            session.add(
                ObraSocial(
                    codigo=codigo,
                    nombre=nombre,
                    validador="imed",
                    dias_vencimiento=60,
                    codigo_financiador=it.get("codigo_financiador"),
                    activo=True,
                )
            )

    session.commit()
