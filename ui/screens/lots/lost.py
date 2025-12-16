import tkinter as tk

from core.image_handler import ImageHandler
from core.imed_cvs_handler import ImedCvsHandler

from ui.controllers.lots_controller import LotsController
from ui.widgets.filters_panel import FiltersPanel
from ui.widgets.lots.tables_container import LotsTablesContainer

from ui.theme.colors import BG_APP


class Lots(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_APP, **kwargs)

        self.controller = LotsController(ImageHandler(), ImedCvsHandler())
        self.controller.bind_on_update(self._render)

        # Layout
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Header / filtros
        self.filters_panel = FiltersPanel(self, controller=self.controller)
        self.filters_panel.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))

        # Tablas
        self.tables = LotsTablesContainer(self)
        self.tables.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _render(self):
        self.tables.images_table.set_rows(self.controller.list_images_tif)
        self.tables.imed_table.set_recetas(self.controller.recetas_imed)
