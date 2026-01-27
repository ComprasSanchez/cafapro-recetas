from __future__ import annotations

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
src = PROJECT_ROOT / "resources"
dst = PROJECT_ROOT / "dist" / "CafaproRecetas" / "resources"

print("SRC:", src)
print("DST:", dst)

if not src.exists():
    raise SystemExit("ERROR: No existe la carpeta resources en el proyecto.")

dst.parent.mkdir(parents=True, exist_ok=True)

if dst.exists():
    shutil.rmtree(dst)

shutil.copytree(src, dst)
print("OK: resources copiado a dist.")
