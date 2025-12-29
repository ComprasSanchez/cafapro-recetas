import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from ui.controllers import LotsController


class Audit(ttk.Frame):
    """
    Pestaña Auditoría (solo UI).
    - Cabecera con filtros (recepción/obra social/etc.)
    - Sub-tabs: Carga / Auditoría
    - Auditoría: tabla izquierda + visor de imagen derecha
    """

    def __init__(self, master):
        super().__init__(master)
        self._imgtk = None
        self._canvas_img_id = None

        self.columnconfigure(0, weight=1)

        # 👇 la fila que tiene el Notebook es la 1, no la 2
        self.rowconfigure(0, weight=0)  # header
        self.rowconfigure(1, weight=1)  # subtabs (crece en alto)

        self._build_header()
        self._build_subtabs()

    def _build_header(self):
        pass
    # ---------------- Sub-tabs (Carga / Auditoría) ----------------
    def _build_subtabs(self):
        sub = ttk.Notebook(self)
        sub.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))  # 👈 nsew

        tab_carga = ttk.Frame(sub)
        tab_aud = ttk.Frame(sub)
        sub.add(tab_carga, text="Carga")
        sub.add(tab_aud, text="Auditoría")

        ttk.Label(tab_carga, text="(pendiente)").pack(padx=10, pady=10)

        tab_aud.columnconfigure(0, weight=1)
        tab_aud.rowconfigure(1, weight=1)

        self._build_auditoria_topbar(tab_aud)
        self._build_auditoria_split(tab_aud)

    # ---------------- Barra superior de Auditoría ----------------
    def _build_auditoria_topbar(self, parent):
        top = ttk.Frame(parent)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        top.columnconfigure(10, weight=1)

        ttk.Label(top, text="Recetas identificadas", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_count = ttk.Label(top, text="0 / 0")
        self.lbl_count.grid(row=0, column=1, padx=(8, 12), sticky="w")

        self.cb_filtro = ttk.Combobox(top, width=18, values=["Todas las recetas", "Con error", "Sin IMED"])
        self.cb_filtro.grid(row=0, column=2)

        # indicadores (placeholders)
        for i, txt in enumerate(["🔴", "🟡", "🟢", "⚪"]):
            ttk.Button(top, text=txt, width=3).grid(row=0, column=3 + i, padx=2)

        ttk.Button(top, text="Auditoría Visual").grid(row=0, column=7, padx=(10, 0))
        ttk.Label(top, text="").grid(row=0, column=10, sticky="ew")

    # ---------------- Split: tabla / imagen ----------------
    def _build_auditoria_split(self, parent):
        paned = ttk.Panedwindow(parent, orient=tk.HORIZONTAL)
        paned.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        self._build_table(left)
        self._build_image_viewer(right)

    # ---------------- Tabla ----------------
    def _build_table(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        # Fila de “filtros” simple (mock)
        filters = ttk.Frame(parent)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        cols = ("nro_receta", "img", "imed", "nro_ref", "imp_rec", "imp_imed", "nro_orden", "estado")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings")

        self.tree.heading("nro_receta", text="Nro de receta")
        self.tree.heading("img", text="Imag...")
        self.tree.heading("imed", text="IMED")
        self.tree.heading("nro_ref", text="Nro de referencia")
        self.tree.heading("imp_rec", text="Importe Reconocido")
        self.tree.heading("imp_imed", text="Importe IMED")
        self.tree.heading("nro_orden", text="Nro Orden")
        self.tree.heading("estado", text="E")

        self.tree.column("nro_receta", width=140, anchor="w")
        self.tree.column("img", width=60, anchor="center")
        self.tree.column("imed", width=60, anchor="center")
        self.tree.column("nro_ref", width=170, anchor="w")
        self.tree.column("imp_rec", width=120, anchor="e")
        self.tree.column("imp_imed", width=110, anchor="e")
        self.tree.column("nro_orden", width=80, anchor="center")
        self.tree.column("estado", width=40, anchor="center")

        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=1, column=0, sticky="nsew")
        yscroll.grid(row=1, column=1, sticky="ns")
        xscroll.grid(row=2, column=0, sticky="ew")

        # (opcional) al seleccionar, podés enganchar preview desde afuera
        # self.tree.bind("<<TreeviewSelect>>", self._on_row_select)

    # ---------------- Visor imagen ----------------
    def _build_image_viewer(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(frame, bg="white", highlightthickness=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=yscroll.set)
        self.set_preview(r"C:\Users\Usuario\sucursales\99029498005\pami_20251209132701009_f.jpg")


    # ---------------- API para usar desde tu controller ----------------
    def set_count(self, identified: int, total: int):
        self.lbl_count.config(text=f"{identified} / {total}")

    def set_rows(self, rows: list[tuple]):
        """
        rows: lista de tuplas con el orden de columnas:
        (nro_receta, img, imed, nro_ref, imp_rec, imp_imed, nro_orden, estado)
        """
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=r)

    def set_preview(self, image_path: str):
        """Muestra un JPG/PNG en el panel derecho (con scroll vertical)."""
        img = Image.open(image_path)

        # Escalado simple para que entre en ancho del canvas
        self.update_idletasks()
        canvas_w = max(300, self.canvas.winfo_width() - 20)
        ratio = canvas_w / img.width
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size)

        self._imgtk = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self._canvas_img_id = self.canvas.create_image(10, 10, anchor="nw", image=self._imgtk)
        self.canvas.configure(scrollregion=(0, 0, img.width + 20, img.height + 20))
