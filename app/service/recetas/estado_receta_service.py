from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class EstadoRecetaItem:
    estado_receta_id: int
    descripcion: str


def _url() -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/estado-receta"


class EstadoRecetaService:
    @staticmethod
    def list() -> list[EstadoRecetaItem]:
        resp = httpx.get(_url(), timeout=600)
        resp.raise_for_status()
        return [
            EstadoRecetaItem(
                estado_receta_id=e["estadoRecetaId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
