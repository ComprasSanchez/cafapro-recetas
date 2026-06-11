from __future__ import annotations

from dataclasses import dataclass

from core.api_client import get_client

from app.config.settings import settings


@dataclass(frozen=True)
class MotivoDebitoItem:
    motivo_debito_id: int
    descripcion: str
    lado: str
    excluyente: str
    codigo: str
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/motivos-debito{path}"


def _to_item(m: dict) -> MotivoDebitoItem:
    return MotivoDebitoItem(
        motivo_debito_id=m["motivoDebitoId"],
        descripcion=m.get("descripcion") or "",
        lado=m.get("lado") or "",
        excluyente=m.get("excluyente") or "N",
        codigo=m.get("codigo") or "",
        activo=bool(m.get("activo", True)),
    )


class MotivosDebitosService:
    @staticmethod
    def list(
        lado: str | None = None,
        activo: bool | None = None,
    ) -> list[MotivoDebitoItem]:
        params: dict = {}
        if lado is not None:
            params["lado"] = lado
        if activo is not None:
            params["activo"] = "true" if activo else "false"
        resp = get_client().get(_url(), params=params)
        resp.raise_for_status()
        return [_to_item(m) for m in resp.json()]

    @staticmethod
    def create(descripcion: str, lado: str) -> MotivoDebitoItem:
        resp = get_client().post(_url(), json={"descripcion": descripcion, "lado": lado})
        resp.raise_for_status()
        return _to_item(resp.json())

    @staticmethod
    def toggle_activo(motivo_id: int) -> None:
        resp = get_client().patch(_url(f"/{int(motivo_id)}/toggle-activo"))
        if resp.status_code == 404:
            raise ValueError("Motivo no encontrado")
        resp.raise_for_status()
