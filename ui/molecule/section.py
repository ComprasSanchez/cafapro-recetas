import tkinter as tk

from ui.atoms.button_section import ButtonSectionItem


class Section(tk.LabelFrame):
    def __init__(self, master, title, items=None, on_click=None):
        super().__init__(master, text=title, fg="white", bg="#444444", bd=2, relief="groove")
        self.on_click = on_click

        if items:
            for item in items:
                self.add_item(item)

    def add_item(self, item):
        lbl = ButtonSectionItem(self, text=item, on_click=self.on_click)
        lbl.pack(fill="x", padx=5, pady=5)