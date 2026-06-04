from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class RolListItem:
    rol_id: int
    descripcion: str


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/roles{path}"


def _to_item(r: dict) -> RolListItem:
    return RolListItem(
        rol_id=r["rolId"],
        descripcion=r["descripcion"] or "",
    )


class RolesService:
    @staticmethod
    def list() -> list[RolListItem]:
        resp = httpx.get(_url(), timeout=10)
        resp.raise_for_status()
        return [_to_item(r) for r in resp.json()]
