import tkinter as tk
from tkinter import ttk

from ui.theme.colors import BG_APP, BG_CARD, BG_BORDER, TEXT_PRIMARY


class ImagesTable(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_APP, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Card container (desktop prolijo)
        card = tk.Frame(self, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        title = tk.Label(card, text="Imágenes TIF", bg=BG_CARD, fg=TEXT_PRIMARY, font=("Segoe UI", 9, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))

        table_frame = tk.Frame(card, bg=BG_CARD)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(
            table_frame,
            columns=("name", "date", "time"),
            show="headings",
        )

        self.table.heading("name", text="Nombre archivo", anchor="w")
        self.table.heading("date", text="Fecha", anchor="center")
        self.table.heading("time", text="Hora", anchor="center")

        self.table.column("name", width=280, stretch=True, anchor="w")
        self.table.column("date", width=90, stretch=False, anchor="center")
        self.table.column("time", width=80, stretch=False, anchor="center")

        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.table.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

        # Zebra
        self.table.tag_configure("odd", background=BG_CARD)
        self.table.tag_configure("even", background="#F7F7F7")

    def set_rows(self, rows: list[dict]):
        self.table.delete(*self.table.get_children())
        for i, row in enumerate(rows):
            tag = "even" if i % 2 == 0 else "odd"

            date_val = (row.get("date", "") or "")
            # Normalizar visual: 04-12-2025 -> 04/12/2025
            if isinstance(date_val, str):
                date_val = date_val.replace("-", "/")

            self.table.insert(
                "",
                "end",
                values=(
                    row.get("name", ""),
                    date_val,
                    row.get("time", ""),
                ),
                tags=(tag,),
            )
