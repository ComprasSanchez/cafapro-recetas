from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class PrestadorItem:
    prestador_id: int
    nombre: str
    codigo: str
    imed: str
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/prestadores{path}"


def _to_item(p: dict) -> PrestadorItem:
    return PrestadorItem(
        prestador_id=p["prestadorId"],
        nombre=p["nombre"] or "(sin nombre)",
        codigo=p["codigo"] or "",
        imed=p["imed"] or "",
        activo=bool(p["activo"]),
    )


class PrestadorService:
    @staticmethod
    def list(*, solo_activos: bool = False) -> list[PrestadorItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        items = [_to_item(p) for p in resp.json()]
        if solo_activos:
            items = [i for i in items if i.activo]
        items.sort(
            key=lambda p: (
                p.nombre == "(sin nombre)",
                p.nombre.casefold(),
                p.codigo.casefold(),
            )
        )
        return items

    @staticmethod
    def get(prestador_id: int) -> PrestadorItem | None:
        resp = get_client().get(_url(f"/{prestador_id}"))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def create(
        *,
        codigo: str,
        nombre: str | None = None,
        imed: str | None = None,
    ) -> None:
        codigo = (codigo or "").strip()
        nombre_clean = (nombre or "").strip() or None
        imed_clean = (imed or "").strip() or None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        payload: dict = {"codigo": codigo}
        if nombre_clean is not None:
            payload["nombre"] = nombre_clean
        if imed_clean is not None:
            payload["imed"] = imed_clean

        resp = get_client().post(_url(), json=payload)
        if resp.status_code == 409:
            raise ValueError(f"Ya existe un prestador con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def update(
        *,
        prestador_id: int,
        codigo: str,
        nombre: str | None = None,
        imed: str | None = None,
    ) -> None:
        codigo = (codigo or "").strip()
        nombre_clean = (nombre or "").strip() or None
        imed_clean = (imed or "").strip() or None

        if not codigo:
            raise ValueError("El código es obligatorio.")

        payload: dict = {"codigo": codigo, "nombre": nombre_clean, "imed": imed_clean}

        resp = get_client().patch(_url(f"/{prestador_id}"), json=payload)
        if resp.status_code == 404:
            raise ValueError(f"No existe prestador_id={prestador_id}")
        if resp.status_code == 409:
            raise ValueError(f"Ya existe otro prestador con código '{codigo}'.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(prestador_id: int) -> None:
        resp = get_client().patch(_url(f"/{prestador_id}"), json={"activo": False})
        if resp.status_code == 404:
            raise ValueError(f"No existe prestador_id={prestador_id}")
        resp.raise_for_status()

    @staticmethod
    def restore(prestador_id: int) -> None:
        resp = get_client().patch(_url(f"/{prestador_id}"), json={"activo": True})
        if resp.status_code == 404:
            raise ValueError(f"No existe prestador_id={prestador_id}")
        resp.raise_for_status()
