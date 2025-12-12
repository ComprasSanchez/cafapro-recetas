import tkinter as tk

from core.image_handler import ImageHandler
from core.imed_cvs_handler import ImedCvsHandler

from ui.screens.lots.lots_controller import LotsController
from ui.screens.lots.lost_filters_panel import LotsFiltersPanel
from ui.screens.lots.tables.lost_table_container import  LotsTablesContainer

from ui.theme.colors import BG_CARD

class Lots(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_CARD, **kwargs)

        self.controller = LotsController(ImageHandler(), ImedCvsHandler())
        self.controller.bind_on_update(self._render)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.filters_panel = LotsFiltersPanel(self, controller=self.controller)
        self.filters_panel.grid(row=0, column=0, sticky="ew")

        self.tables = LotsTablesContainer(self)
        self.tables.grid(row=1, column=0, sticky="nsew")

        self.controller.load_initial(
            imed="99029498005",
            fecha_imgs="11/12/2025",
            obs="pami",
            fecha_imed="04/12/2025",
        )

    def _render(self):
        self.tables.images_table.set_rows(self.controller.list_images_tif)
        self.tables.imed_table.set_recetas(self.controller.recetas_imed)
