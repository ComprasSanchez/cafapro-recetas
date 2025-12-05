import tkinter as tk

from ui.organism.main import Main
from ui.organism.side_bar import SideBar
from ui.template.audit import Audit
from ui.template.lost import Lots



class Layout(tk.Frame):
    def __init__(self, master):
        super().__init__(master)   # color para ver tamaño (podés quitarlo)

        # CONFIGURAMOS EL GRID INTERNO DE CENTRAL
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=0)   # Sidebar ocupa ancho fijo
        self.columnconfigure(1, weight=1)

        # === MAIN ===
        self.main = Main(self)
        self.main.grid(row=0, column=1,sticky="nsew")

        self.main.open_page("Auditoría", Audit)
        self.main.open_page("Lotes Temporales", Lots)

        # === SIDEBAR ===
        sidebar = SideBar(self, self.main.open_page)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

