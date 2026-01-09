from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Archivo


@dataclass(frozen=True)
class ArchivoMatch:
    archivo: Optional[Archivo]
    motivo: str                 # "ok" | "sin_match" | "duplicado"


class ArchivoMatchService:
    @staticmethod
    def match_by_referencias(s: Session, referencias: List[str]) -> ArchivoMatch:
        refs = [str(x).strip() for x in referencias if x]
        if not refs:
            return ArchivoMatch(None, "sin_match")

        for ref in refs:
            matches = s.execute(
                select(Archivo).where(Archivo.nro_referencia == ref)
            ).scalars().all()

            if len(matches) > 1:
                # Duplicado => no insertar nada
                return ArchivoMatch(None, "duplicado")

            if len(matches) == 1:
                return ArchivoMatch(matches[0], "ok")

        return ArchivoMatch(None, "sin_match")
