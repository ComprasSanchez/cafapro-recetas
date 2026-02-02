from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Roles


@dataclass(frozen=True)
class RolListItem:
    rol_id: int
    descripcion: str


class RolesService:
    @staticmethod
    def list(s: Session) -> list[RolListItem]:
        rows = s.execute(
            select(Roles.rol_id, Roles.descripcion).order_by(Roles.descripcion)
        ).all()
        return [RolListItem(rol_id=r[0], descripcion=r[1]) for r in rows]
