import tkinter as tk

class Lots(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#F0FFF0")
        tk.Label(self, text="Lotes temporales", font=("Segoe UI", 16)).pack(pady=20)