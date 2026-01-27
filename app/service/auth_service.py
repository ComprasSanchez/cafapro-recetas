from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Usuarios
from app.security.password_hasher import verify_password


class AuthError(Exception):
    pass


class AuthService:
    @staticmethod
    def authenticate(
        s: Session,
        username: str,
        password: str,
    ) -> Usuarios:
        username = username.strip()

        if not username or not password:
            raise AuthError("Usuario y contraseña son obligatorios.")

        user = s.execute(
            select(Usuarios)
            .where(Usuarios.username == username)
        ).scalar_one_or_none()

        if not user:
            raise AuthError("Usuario o contraseña incorrectos.")

        if not user.activo:
            raise AuthError("El usuario está deshabilitado.")

        if not verify_password(password, user.hash_contrasena):
            raise AuthError("Usuario o contraseña incorrectos.")

        # login OK → actualizar último login
        user.ultimo_login_en = datetime.now()
        s.flush()

        return user
