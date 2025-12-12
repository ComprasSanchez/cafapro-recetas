from __future__ import annotations
from typing import Callable, Optional

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
        self._imed: str = ""
        self._obs: str = ""
        self._fecha_imed: str = ""
        self._fecha_imgs: str = ""

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
        self._fecha_imgs = fecha_imgs
        self._obs = obs
        self._fecha_imed = fecha_imed

        self.list_images_tif = self.images_handler.get_images_tif(imed, fecha_imgs, obs)
        self.recetas_imed, self.detalles_imed = self.imed_handler.read_cvs_by_imed_and_date(imed, fecha_imed)

        self._notify()

    def apply_filters(self) -> None:
        """
        Acá aplicás filtros. Por ahora:
        - Si hay filtro_img_fecha => recarga imágenes por esa fecha
        - Si no => usa la fecha base
        (Extendelo con lo que necesites)
        """
        fecha_imgs = self._fecha_imgs
        if self.filters.filtro_img_fecha:
            # adaptá el formato si tu handler espera dd/mm/yyyy
            fecha_imgs = self.filters.filtro_img_fecha.replace("-", "/")

        self.list_images_tif = self.images_handler.get_images_tif(self._imed, fecha_imgs, self._obs)

        # Si quisieras filtrar recetas_imed en memoria, lo hacés acá.
        # Por ahora no toco IMED (queda como venía en load_initial)

        self._notify()

    def _notify(self) -> None:
        if self._on_update:
            self._on_update()
