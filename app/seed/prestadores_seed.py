import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Prestador


def _norm(s: str | None) -> str:
    return (s or "").strip()

def run (session: Session) -> None:
    base_dir = Path(__file__).resolve().parent

    # ../../field/prestadores.json (ajustá según tu estructura real)
    json_path = base_dir.parent / "seed" / "field" / "prestadores.json"

    if not json_path.exists():
        raise FileNotFoundError(f"No encontré el archivo: {json_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    codigos = sorted({_norm(r.get("codigo")) for r in payload if _norm(r.get("codigo"))})
    if not codigos:
        return

    existentes = session.execute(
        select(Prestador).where(Prestador.codigo.in_(codigos))
    ).scalars().all()
    by_codigo = {p.codigo: p for p in existentes}

    for r in payload:
        codigo = _norm(r.get("codigo"))
        if not codigo:
            continue

        desc = _norm(r.get("descripcion"))
        nombre = desc or None
        # si querés marcar inactivos los "NO USAR":
        activo = "NO USAR" not in desc.upper()

        existente = by_codigo.get(codigo)
        if existente:
            existente.nombre = nombre
            existente.activo = activo
        else:
            session.add(
                Prestador(
                    codigo=codigo,
                    nombre=nombre,
                    activo=activo,
                )
            )