# config/config_manager.py
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QMessageBox, QFileDialog, QWidget


APP_NAME = "Cafapro-Recetas"


def _is_windows() -> bool:
    return os.name == "nt"


def _local_app_data_base() -> Path:
    """
    Carpeta por usuario, sin admin.
    Windows: %LOCALAPPDATA%
    Linux: ~/.local/share
    macOS: ~/Library/Application Support
    """
    home = Path.home()

    if _is_windows():
        return Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))

    if sys.platform == "darwin":
        return home / "Library" / "Application Support"

    return home / ".local" / "share"


def app_data_dir() -> Path:
    """
    Directorio base de la app (por usuario).
    """
    base = _local_app_data_base() / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def normalize_path(p: str) -> str:
    """
    Normaliza rutas para guardar en config.
    En Windows tolera UNC (\\server\\share) y letras (O:\\).
    """
    p = (p or "").strip().strip('"')
    if not p:
        return ""
    # Expand env vars y ~
    p = os.path.expandvars(os.path.expanduser(p))
    return str(Path(p))


def can_read_dir(folder: str) -> tuple[bool, str]:
    try:
        p = Path(folder)
        if not p.exists():
            return False, "La carpeta no existe."
        if not p.is_dir():
            return False, "La ruta no es una carpeta."
        # Intento listar (en red puede fallar si no hay permisos)
        _ = next(iter(p.iterdir()), None)
        return True, ""
    except Exception as e:
        return False, str(e)


def can_write_dir(folder: str) -> tuple[bool, str]:
    """
    Test REAL de escritura (crea un tmp y lo borra).
    """
    try:
        p = Path(folder)
        p.mkdir(parents=True, exist_ok=True)

        test = p / f"__write_test_{int(time.time())}.tmp"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True, ""
    except Exception as e:
        return False, str(e)


@dataclass(frozen=True)
class ConfigKeys:
    image_folder: str = "image_folder"
    imed_folder: str = "imed_folder"
    export_folder: str = "export_folder"  # opcional: carpeta red para exportar
    prefer_unc: str = "prefer_unc"        # opcional


class ConfigManager:
    def __init__(
        self,
        filename: str = "config.json",
        auto_load: bool = True,
        folder_name: str = "config",
    ):
        self.folder_name = folder_name
        self.keys = ConfigKeys()

        self.path = str(self._default_config_path(filename))
        self.data: dict[str, Any] = {}

        if auto_load:
            self.load()

    # -----------------------
    # Paths (AppData)
    # -----------------------
    def _default_config_path(self, filename: str) -> Path:
        cfg_dir = app_data_dir() / self.folder_name
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / filename

    def get_app_data_dir(self) -> Path:
        return app_data_dir()

    def get_output_base_dir(self) -> Path:
        """
        Base de outputs por usuario (siempre escribible sin admin).
        """
        p = self.get_app_data_dir() / "output"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_output_dir(self, recepcion_id: int | str) -> Path:
        """
        Output por recepción:
        ...AppData\\Cafapro-Recetas\\output\\recepciones\\<id>\\
        """
        p = self.get_output_base_dir() / "recepciones" / str(recepcion_id)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_logs_dir(self) -> Path:
        p = self.get_app_data_dir() / "logs"
        p.mkdir(parents=True, exist_ok=True)
        return p

    # -----------------------
    # IO
    # -----------------------
    def load(self) -> bool:
        p = Path(self.path)
        if not p.exists():
            return False
        try:
            self.data = json.loads(p.read_text(encoding="utf-8"))
            return True
        except Exception:
            self.data = {}
            return False

    def save(self, parent: QWidget | None = None) -> bool:
        try:
            p = Path(self.path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self.data, indent=4, ensure_ascii=False), encoding="utf-8")
            return True
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Error guardando configuración",
                "No se pudo guardar el archivo de configuración.\n\n"
                f"Ruta:\n{self.path}\n\n"
                f"Error:\n{e}\n\n"
                "Solución: la configuración se guarda en AppData por usuario.\n"
                "Si esto falla, revisá antivirus / permisos del perfil de Windows.",
            )
            return False

    # -----------------------
    # Folder Picker (soporta servidor / red)
    # -----------------------
    def _pick_directory(self, parent: QWidget | None, title: str, start_dir: str = "") -> str:
        dlg = QFileDialog(parent, title)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)

        # Mejor para navegar "Red" en Windows
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        start_dir = normalize_path(start_dir)
        if start_dir and Path(start_dir).exists():
            dlg.setDirectory(start_dir)
        else:
            dlg.setDirectory(QDir.rootPath())  # This PC

        if dlg.exec() != QFileDialog.DialogCode.Accepted:
            return ""

        paths = dlg.selectedFiles()
        return normalize_path(paths[0]) if paths else ""

    # -----------------------
    # UI Flow
    # -----------------------
    def ask_for_folders(self, parent: QWidget | None = None) -> bool:
        QMessageBox.information(
            parent,
            "Configuración requerida",
            "Necesitamos configurar las carpetas donde trabajar.\n\n"
            "1) Seleccioná la carpeta de Imágenes (puede ser red: \\\\server\\share)\n"
            "2) Seleccioná la carpeta de Descargas de IMED\n\n"
            "Nota: la app guarda sus salidas en AppData (sin admin).",
        )

        image_folder = self._pick_directory(
            parent,
            "Seleccionar carpeta de Imágenes",
            self.get(self.keys.image_folder, "") or "",
        )
        if not image_folder:
            QMessageBox.warning(parent, "Configuración incompleta", "No se seleccionó carpeta de imágenes.")
            return False

        imed_folder = self._pick_directory(
            parent,
            "Seleccionar carpeta de Descargas de IMED",
            self.get(self.keys.imed_folder, "") or "",
        )
        if not imed_folder:
            QMessageBox.warning(parent, "Configuración incompleta", "No se seleccionó carpeta de Descargas de IMED.")
            return False

        # Validación: lectura de ambas
        ok, err = can_read_dir(image_folder)
        if not ok:
            QMessageBox.critical(parent, "Ruta inválida", f"No se puede acceder:\n{image_folder}\n\nDetalle:\n{err}")
            return False

        ok, err = can_read_dir(imed_folder)
        if not ok:
            QMessageBox.critical(parent, "Ruta inválida", f"No se puede acceder:\n{imed_folder}\n\nDetalle:\n{err}")
            return False

        # Guardamos
        self.data.update(
            {
                self.keys.image_folder: image_folder,
                self.keys.imed_folder: imed_folder,
            }
        )
        return self.save(parent=parent)

    def ensure_folders(self, parent: QWidget | None = None) -> bool:
        if self.get(self.keys.image_folder) and self.get(self.keys.imed_folder):
            return True
        return self.ask_for_folders(parent=parent)

    # -----------------------
    # Accessors
    # -----------------------
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True, parent: QWidget | None = None) -> None:
        self.data[key] = value
        if auto_save:
            self.save(parent=parent)

    # -----------------------
    # Helpers directos para tu app
    # -----------------------
    def get_image_folder(self) -> str:
        return normalize_path(self.get(self.keys.image_folder, "") or "")

    def get_imed_folder(self) -> str:
        return normalize_path(self.get(self.keys.imed_folder, "") or "")

    def get_export_folder(self) -> str:
        """
        Opcional: si querés exportar resultados a la red.
        Si está vacío, no exporta.
        """
        return normalize_path(self.get(self.keys.export_folder, "") or "")

    def validate_export_folder_writable(self) -> tuple[bool, str]:
        """
        Si configuraste export_folder (red), valida escritura.
        """
        exp = self.get_export_folder()
        if not exp:
            return True, ""
        return can_write_dir(exp)

