from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config.settings import settings


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class AuthUser:
    usuario_id: int
    username: str
    rol_id: int
    activo: bool


def _url(path: str = "") -> str:
    return f"{settings.API_CAFAPRO.rstrip('/')}/auth{path}"


class AuthService:
    @staticmethod
    def authenticate(username: str, password: str) -> AuthUser:
        username = username.strip()

        if not username or not password:
            raise AuthError("Usuario y contraseña son obligatorios.")

        try:
            resp = httpx.post(
                _url("/login"),
                json={"username": username, "password": password},
                timeout=600,
            )
        except httpx.TransportError as e:
            raise AuthError("No se pudo conectar con el servidor.") from e

        if resp.status_code == 401:
            data = resp.json()
            raise AuthError(data.get("message", "Usuario o contraseña incorrectos."))

        resp.raise_for_status()

        data = resp.json()
        return AuthUser(
            usuario_id=data["usuarioId"],
            username=data["username"],
            rol_id=data["rolId"],
            activo=data["activo"],
        )
