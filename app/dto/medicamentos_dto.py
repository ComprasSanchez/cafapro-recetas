from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MedicamentoDTO:
    """
    DTO mínimo para enriquecer Troqueles SIN cambiar tu tabla.
    - code_alfabeta -> Troqueles.code_alfabeta
    - presentacion  -> Troqueles.presentacion
    - drogas_concat -> Troqueles.droga (concatenación)
    """
    codebar: str
    code_alfabeta: int
    presentacion: Optional[str]
    drogas_concat: Optional[str]

    @staticmethod
    def from_json(data: dict[str, Any]) -> "MedicamentoDTO":
        codebar = str(data.get("codebar") or "").strip()

        ca = data.get("codeAlfaBeta")
        code_alfabeta = int(ca) if ca is not None and str(ca).strip() != "" else 0

        pres = data.get("presentacion")
        presentacion = str(pres).strip() if pres is not None and str(pres).strip() != "" else None

        # drogas: [{idProducto, idDroga}, ...]
        drogas = data.get("drogas") or []
        ids: list[str] = []
        if isinstance(drogas, list):
            for d in drogas:
                if not isinstance(d, dict):
                    continue
                v = d.get("idDroga")
                if v is None:
                    continue
                try:
                    ids.append(str(int(v)))
                except Exception:
                    # si viene raro, lo ignoramos
                    continue

        drogas_concat = ",".join(ids) if ids else None

        return MedicamentoDTO(
            codebar=codebar,
            code_alfabeta=code_alfabeta,
            presentacion=presentacion,
            drogas_concat=drogas_concat,
        )
