import tkinter as tk

from ui.layout.layout import Layout


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Cafapro Recetas")
        self.state("zoomed")

        # --- SOLO ESTO ---
        layout = Layout(self)
        layout.pack(fill="both", expand=True)