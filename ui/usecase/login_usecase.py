from __future__ import annotations

from app.application.auth_application import AuthApplication, AuthError


class LoginUseCase:
    @staticmethod
    def authenticate(*, username: str, password: str):
        return AuthApplication.authenticate(username=username, password=password)
