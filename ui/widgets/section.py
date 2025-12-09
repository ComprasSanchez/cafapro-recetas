import tkinter as tk

class Section(tk.LabelFrame):
    def __init__(self, master, title, items=None, on_click=None):
        super().__init__(master, text=title, fg="white", bg="#444444", bd=2, relief="groove")

        self.on_click = on_click

        if items:
            for item in items:
                self._add_button(item)

    def _add_button(self, text):
        """Crea un botón dentro de la sección y le conecta el callback."""
        btn = tk.Button( self, text=text, bg="#555555", fg="white",)

        btn.pack(fill="x", padx=5, pady=4)

        if self.on_click:
            btn.configure(command=lambda t=text: self.on_click(t))
