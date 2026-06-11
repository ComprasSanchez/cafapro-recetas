from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class TroquelCreatedItem:
    troquel_id: int
    codigo_barra: str
    estado: str
    monto: object
    cantidad: int


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/troqueles{path}"


class TroquelesService:
    @staticmethod
    def create(asociacion_id: int, codigo_barra: str, cantidad: int) -> TroquelCreatedItem:
        payload = {
            "asociacionId": int(asociacion_id),
            "codigoBarra": str(codigo_barra).strip(),
            "cantidad": int(cantidad),
        }
        resp = get_client().post(_url(), json=payload)
        if resp.status_code == 404:
            raise ValueError(resp.json().get("message", "Asociacion no existe"))
        if resp.status_code == 400:
            raise ValueError(resp.json().get("message", "Error de validación"))
        resp.raise_for_status()
        t = resp.json()
        return TroquelCreatedItem(
            troquel_id=t["troquelId"],
            codigo_barra=t.get("codigoBarra") or "",
            estado=t.get("estado") or "",
            monto=t.get("monto") or 0,
            cantidad=int(t.get("cantidad") or 0),
        )

    @staticmethod
    def update(troquel_id: int, cantidad: int) -> None:
        resp = get_client().patch(_url(f"/{int(troquel_id)}"), json={"cantidad": int(cantidad)})
        if resp.status_code == 404:
            raise ValueError(f"Troquel {troquel_id} no existe")
        resp.raise_for_status()

    @staticmethod
    def delete(troquel_id: int) -> None:
        resp = get_client().delete(_url(f"/{int(troquel_id)}"))
        if resp.status_code == 404:
            raise ValueError(f"Troquel {troquel_id} no existe")
        resp.raise_for_status()
