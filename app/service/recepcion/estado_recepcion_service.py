from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class EstadoRecepcionItem:
    estado_recepcion_id: int
    descripcion: str


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/estado-recepcion{path}"


class EstadoRecepcionService:
    @staticmethod
    def list() -> list[EstadoRecepcionItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        return [
            EstadoRecepcionItem(
                estado_recepcion_id=e["estadoRecepcionId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
