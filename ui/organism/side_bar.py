import tkinter as tk
from ui.molecule.section import Section

class SideBar(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#333333", width=220)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self.__menus = {
            "Opciones": ["Buscar Receta", "Carátula", "Listado Débitos"],
            "Pestañas": ["Cerrar", "Cerrar todas"]
        }

        row = 0
        for title, items in self.__menus.items():
            self.add_section(title, items, row)
            row += 1

    def add_section(self, title, items, row):
        """Crea una sección en la barra lateral."""
        section = Section(self, title, items)
        section.grid(row=row, column=0, sticky="nsew", padx=5, pady=8)




