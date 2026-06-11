from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

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
        resp = get_client().get(_url())
        resp.raise_for_status()
        return [
            EstadoRecetaItem(
                estado_receta_id=e["estadoRecetaId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
