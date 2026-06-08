from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class DebitoInput:
    motivo_debito_id: int
    detalle: str | None = None


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/debitos{path}"


class DebitosService:
    @staticmethod
    def replace_for_receta(receta_id: int, items: Iterable[DebitoInput]) -> None:
        payload = [
            {"motivoDebitoId": int(it.motivo_debito_id), "detalle": it.detalle or None}
            for it in items
        ]
        resp = httpx.put(_url(f"/receta/{int(receta_id)}"), json=payload, timeout=600)
        if resp.status_code == 404:
            raise ValueError("Receta no encontrada")
        resp.raise_for_status()
