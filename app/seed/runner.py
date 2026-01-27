from __future__ import annotations

import time

from app.db.session import session_scope

from app.seed.roles_seed import run as run_roles
from app.seed.obra_social_seed import run as run_obra_social
from app.seed.plan_seed import run as run_plan
from app.seed.estado_seguimiento_seed import run as run_estado_seguimiento
from app.seed.motivos_debitos_seed import run as run_motivos_debitos
from app.seed.prestadores_seed import run as run_prestadores
from app.seed.vendedores_seed import run as run_vendedores
from app.seed.estado_receta_seed import run as run_estado_receta
from app.seed.estado_recepcion_seed import run as run_estado_recepcion
from app.seed.seed_admin import run as run_seed_admin


def _step(name: str, fn, s) -> None:
    print(f"➡️  Seed: {name} ...", flush=True)
    t0 = time.perf_counter()
    fn(s)
    dt = time.perf_counter() - t0
    print(f"✅ Seed: {name} OK ({dt:.2f}s)", flush=True)


def seed_all() -> None:
    print("=== SEED START ===", flush=True)

    with session_scope() as s:
        _step("roles", run_roles, s)
        _step("obra_social", run_obra_social, s)
        _step("plan", run_plan, s)
        _step("estado_seguimiento", run_estado_seguimiento, s)
        _step("estado_receta", run_estado_receta, s)
        _step("estado_recepcion", run_estado_recepcion, s)
        _step("motivos_debitos", run_motivos_debitos, s)
        _step("prestadores", run_prestadores, s)
        _step("vendedores", run_vendedores, s)
        _step("usuario", run_seed_admin, s)

    print("✅ Seed OK", flush=True)
    print("=== SEED END ===", flush=True)


if __name__ == "__main__":
    seed_all()

