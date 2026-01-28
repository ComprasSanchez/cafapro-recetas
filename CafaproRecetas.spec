# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_dynamic_libs,
    collect_submodules,
    collect_data_files,
)

# ============================================================
# CONFIG
# ============================================================
APP_NAME = "CafaproRecetas"
ENTRYPOINT = "main.py"

# Raíz del proyecto: usamos el directorio donde está ESTE .spec (vía sys.argv[0])
PROJECT_ROOT = Path(sys.argv[0]).resolve().parent

# Carpeta de recursos externos (debe existir en el proyecto)
RES_DIR = PROJECT_ROOT / "resources"

# Debug útil en el log del build
print(">>> PROJECT_ROOT:", PROJECT_ROOT)
print(">>> RES_DIR:", RES_DIR)
print(">>> RES style exists:", (RES_DIR / "style.qss").exists())
print(">>> RES icon exists:", (RES_DIR / "logo.ico").exists())

# ============================================================
# COLLECT (DLLs / hidden imports)
# ============================================================
hiddenimports: list[str] = []
binaries = []
datas = []

# pyzbar (zbar + libiconv/libzbar)
hiddenimports += collect_submodules("pyzbar")
binaries += collect_dynamic_libs("pyzbar")

# opencv (cv2)
hiddenimports += collect_submodules("cv2")
binaries += collect_dynamic_libs("cv2")
datas += collect_data_files("cv2", include_py_files=False)

# ============================================================
# DATA FILES (Resources al lado del exe)
# Nota: copiamos archivos puntuales (más confiable que copiar carpeta entera)
# ============================================================
datas += [
    (str(RES_DIR / "style.qss"), "resources"),
    (str(RES_DIR / "logo.ico"), "resources"),
]

a = Analysis(
    [ENTRYPOINT],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    # El icono para el EXE tiene que ser un .ico real y existente en el proyecto
    icon=str(RES_DIR / "logo.ico"),
    uac_admin=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)

