from __future__ import annotations

from sqlalchemy import select

from app.db.session import session_scope
from app.db.models import Usuarios, Roles
from app.security.password_hasher import hash_password


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "cafapro123"
ADMIN_ROLE_DESC = "ADMIN"


def run(session) -> None:
        rol = session.execute(
            select(Roles).where(Roles.descripcion == ADMIN_ROLE_DESC)
        ).scalar_one_or_none()

        if not rol:
            rol = Roles(descripcion=ADMIN_ROLE_DESC)
            session.add(rol)
            session.flush()

        # ---- Usuario admin ----
        user = session.execute(
            select(Usuarios).where(Usuarios.username == ADMIN_USERNAME)
        ).scalar_one_or_none()

        if user:
            print("✔ Usuario admin ya existe")
            return

        admin = Usuarios(
            username=ADMIN_USERNAME,
            hash_contrasena=hash_password(ADMIN_PASSWORD),
            rol_id=rol.rol_id,
            activo=True,
        )

        session.add(admin)
        session.flush()

        print("✔ Usuario admin creado correctamente")

