from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class ObraSocialItem:
    obra_social_id: int
    codigo: str
    nombre: str
    validador: str
    dias_vencimiento: int | None
    codigo_financiador: int | None
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/obras-sociales{path}"


def _to_item(o: dict) -> ObraSocialItem:
    return ObraSocialItem(
        obra_social_id=o["obraSocialId"],
        codigo=o["codigo"] or "",
        nombre=o["nombre"] or "",
        validador=o["validador"] or "imed",
        dias_vencimiento=o.get("diasVencimiento"),
        codigo_financiador=o.get("codigoFinanciador"),
        activo=bool(o["activo"]),
    )


class ObraSocialService:
    @staticmethod
    def list(*, solo_activas: bool = False) -> list[ObraSocialItem]:
        resp = httpx.get(_url(), timeout=10)
        resp.raise_for_status()
        items = [_to_item(o) for o in resp.json()]
        if solo_activas:
            items = [i for i in items if i.activo]
        items.sort(key=lambda o: o.nombre.casefold())
        return items

    @staticmethod
    def get(obra_social_id: int) -> ObraSocialItem | None:
        resp = httpx.get(_url(f"/{obra_social_id}"), timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def create(
        *,
        codigo: str,
        nombre: str,
        validador: str = "imed",
        dias_vencimiento: int | str | None = None,
        codigo_financiador: int | str | None = None,
    ) -> None:
        codigo = (codigo or "").strip()
        nombre = (nombre or "").strip()

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios.")

        payload: dict = {"codigo": codigo, "nombre": nombre, "validador": validador}
        if dias_vencimiento not in (None, ""):
            payload["diasVencimiento"] = int(dias_vencimiento)
        if codigo_financiador not in (None, ""):
            payload["codigoFinanciador"] = int(codigo_financiador)

        resp = httpx.post(_url(), json=payload, timeout=10)
        if resp.status_code == 409:
            raise ValueError(f"Ya existe una obra social con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def update(
        *,
        obra_social_id: int,
        codigo: str,
        nombre: str,
        validador: str,
        dias_vencimiento: int | str | None,
        codigo_financiador: int | str | None,
    ) -> None:
        codigo = (codigo or "").strip()
        nombre = (nombre or "").strip()

        if not codigo or not nombre:
            raise ValueError("Código y nombre son obligatorios.")

        payload: dict = {
            "codigo": codigo,
            "nombre": nombre,
            "validador": validador,
            "diasVencimiento": int(dias_vencimiento) if dias_vencimiento not in (None, "") else None,
            "codigoFinanciador": int(codigo_financiador) if codigo_financiador not in (None, "") else None,
        }

        resp = httpx.patch(_url(f"/{obra_social_id}"), json=payload, timeout=10)
        if resp.status_code == 404:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")
        if resp.status_code == 409:
            raise ValueError(f"Ya existe otra obra social con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(obra_social_id: int) -> None:
        resp = httpx.patch(_url(f"/{obra_social_id}"), json={"activo": False}, timeout=10)
        if resp.status_code == 404:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")
        resp.raise_for_status()

    @staticmethod
    def restore(obra_social_id: int) -> None:
        resp = httpx.patch(_url(f"/{obra_social_id}"), json={"activo": True}, timeout=10)
        if resp.status_code == 404:
            raise ValueError(f"No existe obra_social_id={obra_social_id}")
        resp.raise_for_status()
