# config/config_manager.py
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from PySide6.QtWidgets import QMessageBox, QFileDialog, QWidget


class ConfigManager:
    """
    ConfigManager (PySide6)
    - Guarda config en ./config/config.json al lado del .exe (o del proyecto en dev)
    - Crea la carpeta ./config si no existe
    """

    def __init__(self, filename: str = "config.json", auto_load: bool = True, folder_name: str = "config"):
        self.folder_name = folder_name
        self.path = str(self._default_config_path(filename))
        self.data: dict[str, Any] = {}

        if auto_load:
            self.load()

    # -----------------------
    # Paths
    # -----------------------
    def _app_base_dir(self) -> Path:
        # En exe (PyInstaller): carpeta donde está el .exe
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        # En dev: raíz del proyecto (ajustá parents si tu estructura difiere)
        return Path(__file__).resolve().parents[1]

    def _default_config_path(self, filename: str) -> Path:
        base_dir = self._app_base_dir()
        cfg_dir = base_dir / self.folder_name
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / filename

    # -----------------------
    # IO
    # -----------------------
    def load(self) -> bool:
        if not os.path.exists(self.path):
            return False
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            return True
        except Exception:
            self.data = {}
            return False

    def save(self, parent: QWidget | None = None) -> bool:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            print(f"[ConfigManager] Config guardada en: {self.path}")
            return True
        except Exception as e:
            QMessageBox.critical(
                parent,
                "Error guardando configuración",
                "No se pudo guardar el archivo de configuración.\n\n"
                f"Ruta:\n{self.path}\n\n"
                f"Error:\n{e}\n\n"
                "Si instalaste la app en 'Program Files', puede requerir permisos.\n"
                "Solución recomendada: guardar config en AppData.",
            )
            return False

    # -----------------------
    # UI Flow
    # -----------------------
    def ask_for_folders(self, parent: QWidget | None = None) -> bool:
        QMessageBox.information(
            parent,
            "Configuración requerida",
            "Necesitamos configurar las carpetas donde trabajar.\n\n"
            "1) Seleccioná la carpeta de Imágenes.\n"
            "2) Seleccioná la carpeta de Descargas de IMED.",
        )

        image_folder = QFileDialog.getExistingDirectory(
            parent,
            "Seleccionar carpeta de Imágenes",
            self.get("image_folder", "") or "",
            QFileDialog.ShowDirsOnly,
        )
        if not image_folder:
            QMessageBox.warning(parent, "Configuración incompleta", "No se seleccionó carpeta de imágenes.")
            return False

        imed_folder = QFileDialog.getExistingDirectory(
            parent,
            "Seleccionar carpeta de Descargas de IMED",
            self.get("imed_folder", "") or "",
            QFileDialog.ShowDirsOnly,
        )
        if not imed_folder:
            QMessageBox.warning(parent, "Configuración incompleta", "No se seleccionó carpeta de Descargas de IMED.")
            return False

        self.data.update({"image_folder": image_folder, "imed_folder": imed_folder})
        return self.save(parent=parent)

    # -----------------------
    # Accessors
    # -----------------------
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True, parent: QWidget | None = None) -> None:
        self.data[key] = value
        if auto_save:
            self.save(parent=parent)

    def ensure_folders(self, parent: QWidget | None = None) -> bool:
        if self.get("image_folder") and self.get("imed_folder"):
            return True
        return self.ask_for_folders(parent=parent)
