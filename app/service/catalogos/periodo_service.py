from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class PeriodoItem:
    periodo_id: int
    anio: int
    mes: int
    quincena: int
    activo: bool

    @property
    def label(self) -> str:
        return f"{self.anio}-{self.mes:02d} Q{self.quincena}"


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/periodos{path}"


def _to_item(p: dict) -> PeriodoItem:
    return PeriodoItem(
        periodo_id=p["periodoId"],
        anio=p["anio"],
        mes=p["mes"],
        quincena=p["quincena"],
        activo=bool(p["activo"]),
    )


class PeriodoService:
    @staticmethod
    def list(*, solo_activos: bool = False) -> list[PeriodoItem]:
        resp = get_client().get(_url())
        resp.raise_for_status()
        items = [_to_item(p) for p in resp.json()]
        if solo_activos:
            items = [i for i in items if i.activo]
        return items

    @staticmethod
    def get(periodo_id: int) -> PeriodoItem | None:
        resp = get_client().get(_url(f"/{periodo_id}"))
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def create(*, anio: int, mes: int, quincena: int) -> None:
        if quincena not in (1, 2):
            raise ValueError("quincena debe ser 1 o 2")
        if not (1 <= int(mes) <= 12):
            raise ValueError("mes debe estar entre 1 y 12")

        payload = {"anio": int(anio), "mes": int(mes), "quincena": int(quincena)}
        resp = get_client().post(_url(), json=payload)
        if resp.status_code == 409:
            raise ValueError("Ya existe un período con ese año/mes/quincena.")
        resp.raise_for_status()

    @staticmethod
    def update(*, periodo_id: int, anio: int, mes: int, quincena: int) -> None:
        if quincena not in (1, 2):
            raise ValueError("quincena debe ser 1 o 2")
        if not (1 <= int(mes) <= 12):
            raise ValueError("mes debe estar entre 1 y 12")

        payload = {"anio": int(anio), "mes": int(mes), "quincena": int(quincena)}
        resp = get_client().patch(_url(f"/{periodo_id}"), json=payload)
        if resp.status_code == 404:
            raise ValueError(f"No existe periodo_id={periodo_id}")
        if resp.status_code == 409:
            raise ValueError("Ya existe otro período con ese año/mes/quincena.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(periodo_id: int) -> None:
        resp = get_client().patch(_url(f"/{periodo_id}"), json={"activo": False})
        if resp.status_code == 404:
            raise ValueError(f"No existe periodo_id={periodo_id}")
        resp.raise_for_status()

    @staticmethod
    def restore(periodo_id: int) -> None:
        resp = get_client().patch(_url(f"/{periodo_id}"), json={"activo": True})
        if resp.status_code == 404:
            raise ValueError(f"No existe periodo_id={periodo_id}")
        resp.raise_for_status()
