import tkinter as tk

from ui.screens.lots.tables.image_table import ImagesTable
from ui.screens.lots.tables.imed_table import ImedLotsTable


class LotsTablesContainer(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#F5F5F5", **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        self.images_table = ImagesTable(self)
        self.images_table.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.imed_table = ImedLotsTable(self)
        self.imed_table.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
