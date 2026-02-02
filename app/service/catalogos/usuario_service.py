from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Usuarios, Roles
from app.security.password_hasher import hash_password


@dataclass(frozen=True)
class UsuarioListItem:
    usuario_id: int
    username: str
    rol_descripcion: str
    activo: bool
    ultimo_login_en: Optional[object]


class UsuariosService:
    @staticmethod
    def list(s: Session) -> list[UsuarioListItem]:
        rows = s.execute(
            select(
                Usuarios.usuario_id,
                Usuarios.username,
                Roles.descripcion,
                Usuarios.activo,
                Usuarios.ultimo_login_en,
            )
            .join(Roles, Roles.rol_id == Usuarios.rol_id)
            .order_by(Usuarios.usuario_id.desc())
        ).all()

        return [
            UsuarioListItem(
                usuario_id=r[0],
                username=r[1],
                rol_descripcion=r[2],
                activo=r[3],
                ultimo_login_en=r[4],
            )
            for r in rows
        ]

    @staticmethod
    def username_exists(s: Session, username: str) -> bool:
        row = s.execute(
            select(Usuarios.usuario_id).where(Usuarios.username == username.strip())
        ).first()
        return row is not None

    @staticmethod
    def create(s: Session, username: str, password: str, rol_id: int) -> Usuarios:
        username = username.strip()

        if not username:
            raise ValueError("Username es obligatorio.")
        if len(password) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        if UsuariosService.username_exists(s, username):
            raise ValueError("Ya existe un usuario con ese username.")

        user = Usuarios(
            username=username,
            hash_contrasena=hash_password(password),
            rol_id=int(rol_id),
            activo=True,
        )

        s.add(user)
        s.flush()        # obtiene usuario_id
        s.refresh(user)  # refresca campos server_default
        return user

    @staticmethod
    def delete(s: Session, usuario_id: int) -> None:
        user = s.get(Usuarios, usuario_id)
        if not user:
            raise ValueError("El usuario no existe.")
        s.delete(user)
