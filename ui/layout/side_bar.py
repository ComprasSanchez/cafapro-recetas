import tkinter as tk
from ui.widgets.section import Section
from ui.screens.lost import Lots


class SideBar(tk.Frame):
    def __init__(self, master, show_page):
        super().__init__(master, bg="#333333", width=220)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.show_page = show_page

        self.__menus = {
            "Opciones": ["Lotes Temporales"],
            "Pestañas": ["Cerrar", "Cerrar todas"]
        }

        row = 0
        for title, items in self.__menus.items():
            self.add_section(title, items, row)
            row += 1

    def add_section(self, title, items,row):
        """Crea una sección en la barra lateral."""
        section = Section(self, title, items, on_click=self.handle_sidebar_click)
        section.grid(row=row, column=0, sticky="nsew", padx=5, pady=8)

    def handle_sidebar_click(self, option):
        if option == "Lotes Temporales":
            self.show_page("Lotes Temporales", Lots)




