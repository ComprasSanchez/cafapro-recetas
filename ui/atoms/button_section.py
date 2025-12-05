import tkinter as tk

class ButtonSectionItem(tk.Button):
    def __init__(self,master, text, on_click):
        super().__init__(master, text=text, bg="#555555", fg="white")
        self.on_click = on_click
        self.text = text

        self.bind("<Button-1>", self.handle_click)

    def handle_click(self, event):
        self.on_click(self.text)