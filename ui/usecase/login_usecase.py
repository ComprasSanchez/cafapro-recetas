from __future__ import annotations

from app.db.session import session_scope
from app.service.integraciones.auth_service import AuthError, AuthService


class LoginUseCase:
    @staticmethod
    def authenticate(*, username: str, password: str):
        with session_scope() as s:
            return AuthService.authenticate(s, username, password)
