import tkinter as tk
from tkinter import ttk

from ui.layout.footer import Footer
from ui.layout.header import Header
from ui.layout.main import Main
from ui.layout.side_bar import SideBar

from ui.theme.colors import BG_APP


class Layout(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG_APP)

        # GRID PRINCIPAL
        self.rowconfigure(0, weight=0)  # header
        self.rowconfigure(1, weight=1)  # central
        self.rowconfigure(2, weight=0)  # footer
        self.columnconfigure(0, weight=1)

        # HEADER
        header = Header(self)
        header.grid(row=0, column=0, sticky="ew")

        # CENTRAL (sidebar + main)
        central = ttk.Frame(self)
        central.grid(row=1, column=0, sticky="nsew")
        central.rowconfigure(0, weight=1)
        central.columnconfigure(0, weight=0)
        central.columnconfigure(1, weight=1)

        # MAIN
        self.main = Main(central)
        self.main.grid(row=0, column=1, sticky="nsew")

        # SIDEBAR (le pasamos el callback directo a main)
        sidebar = SideBar(central, show_page=self.main.open_page)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.handle_sidebar_click("Lotes Temporales")

        # FOOTER
        footer = Footer(self)
        footer.grid(row=2, column=0, sticky="ew")


