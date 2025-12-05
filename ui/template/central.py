import tkinter as tk

from ui.organism.main import Main
from ui.organism.side_bar import SideBar


class Central(tk.Frame):
    def __init__(self, master):
        super().__init__(master)   # color para ver tamaño (podés quitarlo)

        # CONFIGURAMOS EL GRID INTERNO DE CENTRAL
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0)   # Sidebar ocupa ancho fijo
        self.columnconfigure(1, weight=1)

        # === SIDEBAR ===
        sidebar = SideBar(self)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        # === MAIN ===
        main = Main(self)
        main.grid(row=0, column=1,sticky="nsew")


