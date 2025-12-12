import tkinter as tk
from tkinter import ttk

from ui.widgets.lots.images_table import ImagesTable
from ui.widgets.lots.imed_lots_table import ImedLotsTable
from ui.theme.colors import BG_APP


class LotsTablesContainer(tk.Frame):
    """Contenedor con split resizable (PanedWindow)"""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_APP, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        paned = ttk.Panedwindow(self, orient="horizontal")
        paned.grid(row=0, column=0, sticky="nsew")

        left = tk.Frame(paned, bg=BG_APP)
        right = tk.Frame(paned, bg=BG_APP)

        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.images_table = ImagesTable(left)
        self.images_table.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)

        self.imed_table = ImedLotsTable(right)
        self.imed_table.grid(row=0, column=0, sticky="nsew", padx=(6, 0), pady=0)

        paned.add(left, weight=1)
        paned.add(right, weight=3)
