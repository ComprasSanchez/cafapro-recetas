import tkinter as tk

class ButtonSectionItem(tk.Button):
    def __init__(self,master, text):
        super().__init__(master, text=text, bg="#555555", fg="white")