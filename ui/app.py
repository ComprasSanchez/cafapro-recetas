import tkinter as tk

from config.config_manager import ConfigManager
from ui.layout.layout import Layout
from ui.theme.styles import apply_theme


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        apply_theme(self)

        self.title("Cafapro Recetas")
        self.state("zoomed")
        self.iconbitmap(default="public/logo.ico")

        # Configuración
        self.config_manager = ConfigManager()

        if not self.config_manager.load():
            # Si no existe, la pide al usuario
            self.config_manager.ask_for_folders()
        # --- SOLO ESTO ---
        layout = Layout(self)
        layout.pack(fill="both", expand=True)