from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class PlanItem:
    plan_id: int
    obra_social_id: int
    obra_social: str
    codigo: Optional[str]
    nombre: Optional[str]
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/planes{path}"


def _to_item(p: dict) -> PlanItem:
    return PlanItem(
        plan_id=p["planId"],
        obra_social_id=p["obraSocialId"],
        obra_social=p.get("obraSocial") or "",
        codigo=p.get("codigo"),
        nombre=p.get("nombre"),
        activo=bool(p["activo"]),
    )


class PlanService:
    @staticmethod
    def list(*, solo_activos: bool = False) -> list[PlanItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        items = [_to_item(p) for p in resp.json()]
        if solo_activos:
            items = [i for i in items if i.activo]
        return items

    @staticmethod
    def get(plan_id: int) -> PlanItem | None:
        resp = get_client().get(_url(f"/{plan_id}"))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def create(*, obra_social_id: int, codigo: str | None = None, nombre: str | None = None) -> None:
        payload: dict = {
            "obraSocialId": int(obra_social_id),
            "codigo": (codigo or "").strip() or None,
            "nombre": (nombre or "").strip() or None,
        }
        resp = get_client().post(_url(), json=payload)
        if resp.status_code == 409:
            raise ValueError("Ya existe un plan con esa Obra Social + Nombre + Código.")
        resp.raise_for_status()

    @staticmethod
    def update(*, plan_id: int, obra_social_id: int, codigo: str | None = None, nombre: str | None = None) -> None:
        payload: dict = {
            "obraSocialId": int(obra_social_id),
            "codigo": (codigo or "").strip() or None,
            "nombre": (nombre or "").strip() or None,
        }
        resp = get_client().patch(_url(f"/{plan_id}"), json=payload)
        if resp.status_code == 404:
            raise ValueError(f"No existe plan_id={plan_id}")
        if resp.status_code == 409:
            raise ValueError("Ya existe otro plan con esa Obra Social + Nombre + Código.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(plan_id: int) -> None:
        resp = get_client().patch(_url(f"/{plan_id}"), json={"activo": False})
        if resp.status_code == 404:
            raise ValueError(f"No existe plan_id={plan_id}")
        resp.raise_for_status()

    @staticmethod
    def restore(plan_id: int) -> None:
        resp = get_client().patch(_url(f"/{plan_id}"), json={"activo": True})
        if resp.status_code == 404:
            raise ValueError(f"No existe plan_id={plan_id}")
        resp.raise_for_status()
