from __future__ import annotations

import shutil
from pathlib import Path

APP_NAME = "CafaproRecetas"  # <- nombre de la carpeta dentro de dist/

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_APP = PROJECT_ROOT / "dist" / APP_NAME

# ---------- helpers ----------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def write_env_file(path: Path) -> None:
    # requerido: solo una línea
    path.write_text("DATABASE_URL=\n", encoding="utf-8")

# ---------- 1) copiar resources ----------
src_res = PROJECT_ROOT / "resources"
dst_res = DIST_APP / "resources"

print("PROJECT_ROOT:", PROJECT_ROOT)
print("SRC_RES:", src_res)
print("DST_RES:", dst_res)

if not src_res.exists():
    raise SystemExit("ERROR: No existe la carpeta resources/ en el proyecto.")

ensure_dir(DIST_APP)

if dst_res.exists():
    shutil.rmtree(dst_res)
shutil.copytree(src_res, dst_res)
print("OK: resources copiado.")

# ---------- 2) crear .env.example ----------
env_example = DIST_APP / ".env.example"
write_env_file(env_example)
print("OK: .env.example creado (DATABASE_URL=).")

# ---------- 3) crear .env si no existe ----------
env_file = DIST_APP / ".env"
if env_file.exists():
    print("OK: .env ya existe, NO se modifica.")
else:
    write_env_file(env_file)
    print("OK: .env creado (DATABASE_URL=).")

print("POST BUILD OK.")
