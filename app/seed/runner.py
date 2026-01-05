from __future__ import annotations

from app.db.session import session_scope

from app.seed.roles_seed import run as run_roles
from app.seed.obra_social_seed import run as run_obra_social
from app.seed.plan_seed import run as run_plan
from app.seed.estado_seguimiento_seed import run as run_estado_seguimiento
from app.seed.motivos_debitos import run as run_motivos_debitos
from app.seed.prestadores_seed import run as run_prestadores


def seed_all() -> None:
    with session_scope() as s:
        run_roles(s)
        run_obra_social(s)
        run_plan(s)
        run_estado_seguimiento(s)
        run_motivos_debitos(s)
        run_prestadores(s)


    print("✅ Seed OK")


if __name__ == "__main__":
    seed_all()
