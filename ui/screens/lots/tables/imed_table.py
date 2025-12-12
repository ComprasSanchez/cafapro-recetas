import tkinter as tk
from tkinter import ttk


class ImedLotsTable(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#F0FFF0", **kwargs)
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        frame = tk.LabelFrame(self, text="Lotes / Detalles IMED", bg="#F0FFF0")
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.table = ttk.Treeview(
            frame,
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

        columns = [
            ("code", "Nro Receta", "w"),
            ("beneficiary", "Beneficiario", "w"),
            ("date", "Fecha", "center"),
            ("reference", "Nro Referencia", "w"),
            ("amount_neto", "Importe Neto", "e"),
            ("amount", "Importe Gral", "e"),
            ("amount_obs", "Importe Obs", "e"),
        ]

        for key, title, anchor in columns:
            self.table.heading(key, text=title, anchor=anchor)
            self.table.column(key, anchor=anchor)

        self.table.grid(row=0, column=0, sticky="nsew")

        scrollbar_y = ttk.Scrollbar(frame, orient="vertical", command=self.table.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        scrollbar_x = ttk.Scrollbar(frame, orient="horizontal", command=self.table.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        self.table.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
        )

    def set_recetas(self, recetas_por_ref: dict):
        self.table.delete(*self.table.get_children())

        for _, receta in recetas_por_ref.items():
            self.table.insert(
                "",
                "end",
                values=(
                    receta.get("Nro Receta", ""),
                    receta.get("Beneficiario", ""),
                    receta.get("Fecha", ""),
                    receta.get("Nro Referencia", ""),
                    receta.get("Importe Pami", ""),
                    receta.get("Importe Gral", ""),
                    receta.get("A Cargo Entidad", ""),
                ),
            )

