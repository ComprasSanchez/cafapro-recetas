import tkinter as tk
from tkinter import ttk

from ui.organism.header import Header
from ui.organism.footer import Footer
from ui.template.central import Central


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Cafapro Recetas")
        self.state("zoomed")

        # === ROOT CONTAINER ===
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        # ROOT GRID
        root.rowconfigure(0, weight=0)     # HEADER
        root.rowconfigure(1, weight=2)     # CENTRAL
        root.rowconfigure(2, weight=0)     # FOOTER
        root.columnconfigure(0, weight=1)

        # HEADER
        header = Header(root)
        header.grid(row=0, column=0, sticky="ew")

        central = Central(root)
        central.grid(row=1, column=0, sticky="nsew")


        # FOOTER
        footer = Footer(root)
        footer.grid(row=2, column=0,sticky="ew")
        footer.grid_propagate(False)


