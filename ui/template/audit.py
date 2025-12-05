import tkinter as tk

class Audit(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#F5F5F5")
        tk.Label(self, text="Auditoría", font=("Segoe UI", 16)).pack(pady=20)