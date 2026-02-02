from __future__ import annotations

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.models import ObraSocial, Plan


def _norm(s: str | None) -> str:
    return (s or "").strip()

PLANES = [
    {
        "codigo": "PT                  ",
        "nombre": "PAMI TIRAS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PMM                 ",
        "nombre": "PAMI MANUAL",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PI                  ",
        "nombre": "PAMI INSULINAS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PCI                 ",
        "nombre": "PAMI CRÓNICOS INSULINAS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PCC                 ",
        "nombre": "PAMI CRÓNICOS CLOZAPINAS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PC                  ",
        "nombre": "PAMI CRÓNICOS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PAO                 ",
        "nombre": "ANTIDIABETICOS ORALES",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PAMIVIVIRMEJ        ",
        "nombre": "VIVIR MEJOR",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "PADBT               ",
        "nombre": "ACCESORIOS DBT",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "MUE                 ",
        "nombre": "MEDICAMENTOS DE USO EVENTUAL",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "1562                ",
        "nombre": "PAMI COSEGUROS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "1299                ",
        "nombre": "PAMI RESOLUCION 337",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "1299                ",
        "nombre": "PAMI RES-337 COSEGUROS",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "1147                ",
        "nombre": "PAMI POR RAZONES SOCIALES",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "1146                ",
        "nombre": "PAMI POR VIA DE EXCEPCION",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "167                 ",
        "nombre": "PAMI ONCOLOGICO",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "26                  ",
        "nombre": "PAMI AMBU",
        "codigo_obra_social": "80                  "
    },
    {
        "codigo": "AT                  ",
        "nombre": "APROSS TIRAS",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AR120R              ",
        "nombre": "APROSS RESOLUCION 120(RES)",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AR120               ",
        "nombre": "APROSS RESOLUCION 120",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AMT                 ",
        "nombre": "APROSS MIXTA TIRAS",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AMI                 ",
        "nombre": "APROSS MIXTA INSULINAS",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AAMP                ",
        "nombre": "APROSS AMPARO",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "AAM                 ",
        "nombre": "APROSS AMBULATORIO MANUAL",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1700                ",
        "nombre": "APROSS INSULINAS",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1626                ",
        "nombre": "APROSS RESOL MINIST 398/09",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1561                ",
        "nombre": "APROSS RES 40/5 COSEG",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1560                ",
        "nombre": "APROSS RES 40/5 AMBULAT",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1085                ",
        "nombre": "APROSS ONCOLOGICO",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1084                ",
        "nombre": "APROSS TRAT ESPECIALES",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "1020                ",
        "nombre": "APROSS CRONICOS",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "707                 ",
        "nombre": "APROSS PMI",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "704                 ",
        "nombre": "APROSS AMBULATORIO",
        "codigo_obra_social": "12                  "
    },
    {
        "codigo": "704                 ",
        "nombre": "APROSS REFACTURADAS",
        "codigo_obra_social": "12                  "
    },
]


def run(session: Session) -> None:
    """
    Inserta/actualiza Planes.
    - activo=True siempre
    - resuelve FK por obra_social.codigo
    - upsert por plan.codigo (debe ser unique)
    """
    # cache de obras sociales por codigo
    codigos_os = sorted({_norm(p["codigo_obra_social"]) for p in PLANES if _norm(p["codigo_obra_social"])})
    obras = session.execute(
        select(ObraSocial).where(ObraSocial.codigo.in_(codigos_os))
    ).scalars().all()
    obra_by_codigo = {o.codigo: o for o in obras}

    faltantes = [c for c in codigos_os if c not in obra_by_codigo]
    if faltantes:
        raise ValueError(
            "No existen estas obras sociales (obra_social.codigo) y son requeridas por planes:\n"
            + "\n".join(f"- {c}" for c in faltantes)
        )

    for p in PLANES:
        plan_codigo = _norm(p["codigo"])
        nombre = _norm(p["nombre"])
        os_codigo = _norm(p["codigo_obra_social"])

        obra = obra_by_codigo[os_codigo]

        existente = session.execute(
            select(Plan).where(
                and_(
                    Plan.obra_social_id == obra.obra_social_id,
                    Plan.codigo == plan_codigo,
                    Plan.nombre == nombre,
                )
            )
        ).scalar_one_or_none()
        if existente:
            existente.nombre = nombre  # o existente.nombre = desc
            existente.activo = True
            existente.obra_social_id = obra.obra_social_id
        else:
            nuevo = Plan(
                codigo=plan_codigo,
                nombre=nombre,
                activo=True,
                obra_social_id=obra.obra_social_id,
            )
            session.add(nuevo)

    session.commit()

