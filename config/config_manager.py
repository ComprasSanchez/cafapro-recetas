# config/config_manager.py
import json
import os
from tkinter import filedialog, messagebox
from typing import Any, Optional


class ConfigManager:
    def __init__(self, filename: str = "config.json", auto_load: bool = True):
        base_dir = os.path.dirname(os.path.abspath(__file__))  # carpeta /config
        self.path = os.path.join(base_dir, filename)           # config/config.json
        self.data: dict[str, Any] = {}

        if auto_load:
            self.load()

    def load(self) -> bool:
        if not os.path.exists(self.path):
            return False

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return True

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

        print(f"[ConfigManager] Config guardada en: {self.path}")

    def ask_for_folders(self, parent=None) -> bool:
        messagebox.showinfo(
            "Configuración requerida",
            "Necesitamos configurar las carpetas donde trabajar.\n"
            "Selecciona la carpeta de imágenes cuando se te solicite.",
            parent=parent,
        )

        image_folder = filedialog.askdirectory(
            title="Seleccionar carpeta de Imágenes",
            parent=parent
        )

        imed_folder = filedialog.askdirectory(
            title="Seleccionar carpeta de Descargas de Imed",
            parent=parent
        )

        if not image_folder:
            messagebox.showwarning(
                "Configuración incompleta",
                "No se seleccionó ninguna carpeta de imágenes.\n"
                "La configuración no se guardará.",
                parent=parent,
            )
            return False

        if not imed_folder:
            messagebox.showwarning(
                "Configuración incompleta",
                "No se seleccionó ninguna carpeta de Descargas de Imed.\n"
                "La configuración no se guardará.",
                parent=parent,
            )
            return False

        self.data = {
            "image_folder": image_folder,
            "imed_folder": imed_folder,
        }

        self.save()
        return True

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Obtiene un valor de la configuración.

        :param key: Clave a buscar en el JSON.
        :param default: Valor por defecto si la clave no existe.
        :return: Valor asociado a la clave o default si no está.
        """
        return self.data[key] if key in self.data else default

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """
        Setea un valor en la configuración y opcionalmente guarda.

        :param key: Clave.
        :param value: Valor a guardar.
        :param auto_save: Si es True, guarda automáticamente el archivo.
        """
        self.data[key] = value
        if auto_save:
            self.save()
