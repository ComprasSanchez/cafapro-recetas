from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Archivo


@dataclass(frozen=True)
class MatchResult:
    # ref -> archivo (si es único), ref -> None si no existe o duplicado
    ref_to_archivo: Dict[str, Optional[Archivo]]
    duplicated_refs: set[str]
    missing_refs: set[str]


class ArchivoMatchServiceFast:
    @staticmethod
    def match_all_refs(s: Session, refs: List[str]) -> MatchResult:
        refs_norm = [str(r).strip() for r in refs if r]
        refs_set = set(refs_norm)
        if not refs_set:
            return MatchResult(ref_to_archivo={}, duplicated_refs=set(), missing_refs=set())

        rows = s.execute(
            select(Archivo).where(Archivo.nro_referencia.in_(list(refs_set)))
        ).scalars().all()

        # agrupar por nro_referencia
        by_ref: Dict[str, List[Archivo]] = {}
        for a in rows:
            by_ref.setdefault(str(a.nro_referencia), []).append(a)

        duplicated = {ref for ref, arr in by_ref.items() if len(arr) > 1}
        missing = {ref for ref in refs_set if ref not in by_ref}

        ref_to_archivo: Dict[str, Optional[Archivo]] = {}
        for ref in refs_set:
            if ref in duplicated:
                ref_to_archivo[ref] = None
            elif ref in by_ref:
                ref_to_archivo[ref] = by_ref[ref][0]
            else:
                ref_to_archivo[ref] = None

        return MatchResult(ref_to_archivo=ref_to_archivo, duplicated_refs=duplicated, missing_refs=missing)
