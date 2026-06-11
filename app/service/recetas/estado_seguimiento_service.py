from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class EstadoSeguimientoItem:
    estado_seguimiento_id: int
    descripcion: str


def _url() -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/estado-seguimiento"


class EstadoSeguimientoService:
    @staticmethod
    def list() -> list[EstadoSeguimientoItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        return [
            EstadoSeguimientoItem(
                estado_seguimiento_id=e["estadoSeguimientoId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
