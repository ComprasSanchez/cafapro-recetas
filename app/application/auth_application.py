from __future__ import annotations

from app.service.integraciones.auth_service import AuthError, AuthService


class AuthApplication:
    @staticmethod
    def authenticate(*, username: str, password: str):
        return AuthService.authenticate(username, password)


__all__ = ["AuthApplication", "AuthError"]
