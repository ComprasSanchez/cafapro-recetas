import tkinter as tk
from tkinter import ttk

from ui.theme.colors import BG_APP, BG_CARD, BG_BORDER, TEXT_PRIMARY


class ImedLotsTable(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=BG_APP, **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        card = tk.Frame(self, bg=BG_CARD, highlightthickness=1, highlightbackground=BG_BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        title = tk.Label(
            card,
            text="Lotes / Detalles IMED",
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 6))

        table_frame = tk.Frame(card, bg=BG_CARD)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(
            table_frame,
            columns=(
                "code",
                "beneficiary",
                "date",
                "reference",
                "amount_neto",
                "amount",
                "amount_obs",
            ),
            show="headings",
        )

        cols = [
            ("code", "Nro Receta", "w", 120, False),
            ("beneficiary", "Beneficiario", "w", 160, True),
            ("date", "Fecha", "center", 90, False),
            ("reference", "Nro Referencia", "w", 180, False),
            ("amount_neto", "Importe Neto", "e", 110, False),
            ("amount", "Importe Gral", "e", 110, False),
            ("amount_obs", "Importe Obs", "e", 110, False),
        ]

        for key, title_text, anchor, width, stretch in cols:
            self.table.heading(key, text=title_text, anchor=anchor)
            self.table.column(key, anchor=anchor, width=width, stretch=stretch)

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

    def set_recetas(self, recetas_por_ref: dict):
        self.table.delete(*self.table.get_children())

        for i, (_, receta) in enumerate(recetas_por_ref.items()):
            tag = "even" if i % 2 == 0 else "odd"

            fecha = (receta.get("Fecha", "") or "")
            if isinstance(fecha, str):
                fecha = fecha.replace("-", "/")

            self.table.insert(
                "",
                "end",
                values=(
                    receta.get("Nro Receta", ""),
                    receta.get("Beneficiario", ""),
                    fecha,
                    receta.get("Nro Referencia", ""),
                    receta.get("Importe Pami", ""),
                    receta.get("Importe Gral", ""),
                    receta.get("A Cargo Entidad", ""),
                ),
                tags=(tag,),
            )
