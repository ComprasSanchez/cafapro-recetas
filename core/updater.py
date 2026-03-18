from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from PySide6.QtWidgets import QMessageBox

from core.version import APP_VERSION

UPDATE_API_URL = "http://cafapro-updates-api-production.up.railway.app/app/version"


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    download_url: str
    mandatory: bool


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def is_newer(latest: str, current: str) -> bool:
    def parse(v: str):
        return tuple(int(x) for x in v.split("."))

    return parse(latest) > parse(current)


def download_file(url: str) -> Path:
    temp_dir = Path(os.getenv("TEMP") or str(Path.cwd()))
    target = temp_dir / "CafaproRecetasUpdate.exe"

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(target, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return target


def run_installer_and_exit(installer_path: Path):
    subprocess.Popen([str(installer_path)], shell=True)
    os._exit(0)


def get_pending_update() -> UpdateInfo | None:
    if not is_frozen():
        return None

    try:
        response = requests.get(UPDATE_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        latest_version = data.get("latest_version")
        download_url = data.get("download_url")
        mandatory = data.get("mandatory", False)

        if not latest_version or not download_url:
            return None

        if not is_newer(latest_version, APP_VERSION):
            return None

        return UpdateInfo(
            latest_version=str(latest_version),
            download_url=str(download_url),
            mandatory=bool(mandatory),
        )

    except Exception:
        return None


def apply_update(update: UpdateInfo, *, status_cb: Callable[[str], None] | None = None) -> None:
    if status_cb:
        status_cb(f"Descargando actualización {update.latest_version}…")

    installer_path = download_file(update.download_url)

    if status_cb:
        status_cb("Iniciando instalador…")

    run_installer_and_exit(installer_path)


def check_for_updates(app):
    update = get_pending_update()
    if not update:
        return

    if not update.mandatory:
        reply = QMessageBox.question(
            None,
            "Actualización disponible",
            f"Hay una nueva versión ({update.latest_version}).\n\n¿Desea actualizar ahora?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

    apply_update(update)
