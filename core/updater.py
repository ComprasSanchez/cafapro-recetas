import sys
import os
import requests
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QMessageBox

from core.version import APP_VERSION

UPDATE_API_URL = "http://localhost:3000/app/version"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def is_newer(latest: str, current: str) -> bool:
    def parse(v: str):
        return tuple(int(x) for x in v.split("."))

    return parse(latest) > parse(current)


def download_file(url: str) -> Path:
    temp_dir = Path(os.getenv("TEMP"))
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


def check_for_updates(app):
    if not is_frozen():
        return

    try:
        response = requests.get(UPDATE_API_URL, timeout=5)
        response.raise_for_status()
        data = response.json()

        latest_version = data.get("latest_version")
        download_url = data.get("download_url")
        mandatory = data.get("mandatory", False)

        if not latest_version or not download_url:
            return

        if not is_newer(latest_version, APP_VERSION):
            return

        if not mandatory:
            reply = QMessageBox.question(
                None,
                "Actualización disponible",
                f"Hay una nueva versión ({latest_version}).\n\n¿Desea actualizar ahora?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

        installer_path = download_file(download_url)
        run_installer_and_exit(installer_path)

    except Exception:
        pass