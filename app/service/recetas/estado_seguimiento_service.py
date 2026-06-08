from __future__ import annotations

from dataclasses import dataclass

import httpx

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
        resp = httpx.get(_url(), timeout=600)
        resp.raise_for_status()
        return [
            EstadoSeguimientoItem(
                estado_seguimiento_id=e["estadoSeguimientoId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
