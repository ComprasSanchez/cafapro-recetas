from __future__ import annotations

import os
from typing import Callable, Optional

from tkinter import messagebox

from core.process_tif import TiffProcessor
from ui.shared.filter_state import FilterState


class LotsController:

    def __init__(self, images_handler, imed_handler):
        self.images_handler = images_handler
        self.imed_handler = imed_handler

        # Estado de filtros (GENERAL)
        self.filters = FilterState()

        # Data que consume la vista
        self.list_images_tif: list[dict] = []
        self.recetas_imed: dict = {}
        self.detalles_imed: dict = {}

        # Callback para que la UI se actualice
        self._on_update: Optional[Callable[[], None]] = None

        # Contexto base (para recargas)
        self._imed: str = "99029498005"
        self._obs: str = self.filters.obra_social
        self._fecha_imed_base: str = ""
        self._fecha_imgs_base: str = ""

    def bind_on_update(self, cb: Callable[[], None]) -> None:
        self._on_update = cb

    def set_filter(self, **kwargs) -> None:
        """Permite setear filtros desde cualquier clase."""
        for k, v in kwargs.items():
            if hasattr(self.filters, k):
                setattr(self.filters, k, v)

    def load_initial(self, imed: str, fecha_imgs: str, obs: str, fecha_imed: str) -> None:
        """Carga inicial (o recarga completa)."""
        self._imed = imed
        self._fecha_imgs_base = fecha_imgs
        self._obs = obs
        self._fecha_imed_base = fecha_imed

        self.reload_images()
        self.reload_imed()

        self._notify()

    # ─────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────
    def reload_images(self) -> None:
        fecha_imgs = self.filters.filtro_img_fecha or self._fecha_imgs_base
        try:
            self.list_images_tif = self.images_handler.get_images_tif(self._imed, fecha_imgs, self._obs)
        except FileNotFoundError:
            messagebox.showwarning(
                "Imágenes",
                f"No se encuentra la ruta de imágenes para:\nIMED: {self._imed}\nFecha: {fecha_imgs}\nObs: {self._obs}",
            )
            self.list_images_tif = []
        except Exception as e:
            messagebox.showwarning(
                "Imágenes",
                f"Error al cargar imágenes:\n{e}",
            )
            self.list_images_tif = []
        self._notify()

    def reload_imed(self) -> None:
        fecha_imed = self.filters.filtro_aut_fecha or self._fecha_imed_base
        try:
            self.recetas_imed, self.detalles_imed = self.imed_handler.read_cvs_by_imed_and_date(self._imed, fecha_imed)
        except FileNotFoundError:
            messagebox.showwarning(
                "IMED",
                f"No se encuentra el archivo IMED para:\nIMED: {self._imed}\nFecha: {fecha_imed}",
            )
            self.recetas_imed, self.detalles_imed = {}, {}
        except Exception as e:
            messagebox.showwarning(
                "IMED",
                f"Error al leer archivo IMED:\n{e}",
            )
            self.recetas_imed, self.detalles_imed = {}, {}
        self._notify()

    def process_tif(self):
        processed_images = TiffProcessor()
        if len(self.list_images_tif) == 0:
            messagebox.showwarning(
                "Procesado de Imágenes",
                "No hay imágenes agregadas.",
            )
            return
        for image in self.list_images_tif:
            processed_images.process(image["full_path"], os.path.dirname(image["full_path"]))

    def _notify(self) -> None:
        if self._on_update:
            self._on_update()
