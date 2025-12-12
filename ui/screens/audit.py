import tkinter as tk
from ui.theme.colors import BG_APP

class Audit(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG_APP)
        tk.Label(self, text="Auditoría", font=("Segoe UI", 16)).pack(pady=20)