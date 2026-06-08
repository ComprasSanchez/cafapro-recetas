from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.config.settings import settings


@dataclass(frozen=True)
class UsuarioListItem:
    usuario_id: int
    username: str
    rol_descripcion: str
    activo: bool
    ultimo_login_en: Optional[object]


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/usuarios{path}"


def _to_item(u: dict) -> UsuarioListItem:
    return UsuarioListItem(
        usuario_id=u["usuarioId"],
        username=u["username"] or "",
        rol_descripcion=u.get("rolDescripcion") or "",
        activo=bool(u["activo"]),
        ultimo_login_en=u.get("ultimoLoginEn"),
    )


class UsuariosService:
    @staticmethod
    def list() -> list[UsuarioListItem]:
        resp = httpx.get(_url(), timeout=600)
        resp.raise_for_status()
        return [_to_item(u) for u in resp.json()]

    @staticmethod
    def create(*, username: str, password: str, rol_id: int) -> None:
        username = username.strip()
        if not username:
            raise ValueError("Username es obligatorio.")
        if len(password) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")

        payload = {"username": username, "password": password, "rolId": int(rol_id)}
        resp = httpx.post(_url(), json=payload, timeout=600)
        if resp.status_code == 409:
            raise ValueError("Ya existe un usuario con ese username.")
        resp.raise_for_status()

    @staticmethod
    def delete_logico(usuario_id: int) -> None:
        resp = httpx.patch(_url(f"/{usuario_id}"), json={"activo": False}, timeout=600)
        if resp.status_code == 404:
            raise ValueError("El usuario no existe.")
        resp.raise_for_status()

    @staticmethod
    def restore(usuario_id: int) -> None:
        resp = httpx.patch(_url(f"/{usuario_id}"), json={"activo": True}, timeout=600)
        if resp.status_code == 404:
            raise ValueError("El usuario no existe.")
        resp.raise_for_status()
