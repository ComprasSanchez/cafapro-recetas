import tkinter as tk
from ui.theme.colors import BG_APP

class Footer(tk.Frame):
    def __init__(self, master):
        super().__init__(master,  bg=BG_APP, bd=1, height=24)