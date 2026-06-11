from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class VendedorItem:
    vendedor_id: int
    codigo: str
    descripcion: str
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/vendedores{path}"


def _to_item(v: dict) -> VendedorItem:
    return VendedorItem(
        vendedor_id=v["vendedorId"],
        codigo=v["codigo"] or "",
        descripcion=v["descripcion"] or "",
        activo=bool(v["activo"]),
    )


class VendedoresService:
    @staticmethod
    def list(*, solo_activos: bool = False) -> list[VendedorItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        items = [_to_item(v) for v in resp.json()]
        if solo_activos:
            items = [i for i in items if i.activo]
        return items

    @staticmethod
    def get(vendedor_id: int) -> VendedorItem | None:
        resp = get_client().get(_url(f"/{vendedor_id}"))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def create(*, codigo: str, descripcion: str | None = None) -> None:
        codigo = (codigo or "").strip()
        descripcion_clean = (descripcion or "").strip() or None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        payload: dict = {"codigo": codigo}
        if descripcion_clean is not None:
            payload["descripcion"] = descripcion_clean

        resp = get_client().post(_url(), json=payload)
        if resp.status_code == 409:
            raise ValueError(f"Ya existe un vendedor con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def update(*, vendedor_id: int, codigo: str, descripcion: str | None = None) -> None:
        codigo = (codigo or "").strip()
        descripcion_clean = (descripcion or "").strip() or None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        payload: dict = {"codigo": codigo, "descripcion": descripcion_clean}

        resp = get_client().patch(_url(f"/{vendedor_id}"), json=payload)
        if resp.status_code == 404:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")
        if resp.status_code == 409:
            raise ValueError(f"Ya existe otro vendedor con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(vendedor_id: int) -> None:
        resp = get_client().patch(_url(f"/{vendedor_id}"), json={"activo": False})
        if resp.status_code == 404:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")
        resp.raise_for_status()

    @staticmethod
    def restore(vendedor_id: int) -> None:
        resp = get_client().patch(_url(f"/{vendedor_id}"), json={"activo": True})
        if resp.status_code == 404:
            raise ValueError(f"No existe vendedor_id={vendedor_id}")
        resp.raise_for_status()
