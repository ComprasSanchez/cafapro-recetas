from __future__ import annotations

from dataclasses import dataclass

import httpx

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
        resp = httpx.get(_url(), timeout=600)
        resp.raise_for_status()
        return [
            EstadoRecepcionItem(
                estado_recepcion_id=e["estadoRecepcionId"],
                descripcion=e.get("descripcion") or "",
            )
            for e in resp.json()
        ]
