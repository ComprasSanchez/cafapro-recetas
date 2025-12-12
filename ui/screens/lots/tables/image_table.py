import tkinter as tk
from tkinter import ttk


class ImagesTable(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#F0FFF0", **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        frame = tk.LabelFrame(self, text="Imágenes TIF", bg="#F0FFF0")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(
            frame,
            columns=("name", "date", "time"),
            show="headings",
        )

        self.table.heading("name", text="Nombre archivo", anchor="w")
        self.table.heading("date", text="Fecha", anchor="center")
        self.table.heading("time", text="Hora", anchor="center")

        self.table.column("name", anchor="w")
        self.table.column("date", anchor="center")
        self.table.column("time", anchor="center")

        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar_y = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        scrollbar_x = ttk.Scrollbar(frame, orient="horizontal", command=self.table.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.table.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

    def set_rows(self, rows: list[dict]):
        self.table.delete(*self.table.get_children())
        for row in rows:
            self.table.insert(
                "",
                "end",
                values=(
                    row.get("name", ""),
                    row.get("date", ""),
                    row.get("time", ""),
                ),
            )
