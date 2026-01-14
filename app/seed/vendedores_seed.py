import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Vendedores


def _norm(s: str | None) -> str:
    return (s or "").strip()

def run (session: Session) -> None:
    base_dir = Path(__file__).resolve().parent

    # ../../field/prestadores.json (ajustá según tu estructura real)
    json_path = base_dir.parent / "seed" / "field" / "vendedores.json"

    if not json_path.exists():
        raise FileNotFoundError(f"No encontré el archivo: {json_path}")

    payload = json.loads(json_path.read_text(encoding="utf-8"))

    codigos = sorted({_norm(r.get("codigo")) for r in payload if _norm(r.get("codigo"))})
    if not codigos:
        return


    for r in payload:
        codigo = _norm(r.get("codigo"))
        if not codigo:
            continue

        desc = _norm(r.get("descripcion"))
        session.add(
                Vendedores(
                    codigo=codigo,
                    descripcion=desc,
                )
            )