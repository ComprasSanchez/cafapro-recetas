import tkinter as tk
from tkinter import ttk

from core.image_handler import ImageHandler
from core.imed_cvs_handler import ImedCvsHandler


class Lots(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#F5F5F5", **kwargs)

        # ─────────────────────────────────────
        # 1) Obtener datos iniciales
        # ─────────────────────────────────────
        self.images_handler = ImageHandler()
        self.imed_cvs_handler = ImedCvsHandler()
        self.list_images_tif = self.images_handler.get_images_tif(
            "99029498005", "11/12/2025", "pami"
        )
        self.recetas_imed, self.detalles_imed = self.imed_cvs_handler.read_cvs_by_imed_and_date(
            "99029498005", "04/12/2025"
        )

        # Layout principal
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        self._build_header()
        self._build_horizontal_tables()
        self._populate_images_table()

    # ─────────────────────────────────────────
    # CABECERA CON FILTROS
    # ─────────────────────────────────────────
    def _build_header(self):
        header = tk.Frame(self, bg="#E6FFE6", padx=8, pady=6)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(20, weight=1)  # empuja lo que sobre a la derecha

        # ───────── FILA 0: Nº Recepción + Obra social ─────────
        tk.Label(header, text="N° Recepción:", bg="#E6FFE6").grid(row=0, column=0, sticky="w")

        self.var_recepcion = tk.StringVar(value="")  # ej: 87505
        tk.Entry(header, textvariable=self.var_recepcion, width=8).grid(
            row=0, column=1, padx=(2, 4), sticky="w"
        )

        # Botón "+" (nuevo)
        tk.Button(
            header, text="+", width=2, command=self._on_new_recepcion
        ).grid(row=0, column=2, padx=(0, 2))

        # Botón editar (icono lápiz medio fake)
        tk.Button(
            header, text="✎", width=2, command=self._on_edit_recepcion
        ).grid(row=0, column=3, padx=(0, 8))

        # Obra social
        tk.Label(header, text="Obra social:", bg="#E6FFE6").grid(row=0, column=4, sticky="w")
        self.var_obra_social = tk.StringVar(value="PAMI")
        tk.Entry(header, textvariable=self.var_obra_social, width=15).grid(
            row=0, column=5, padx=(2, 8), sticky="w"
        )

        # ───────── FILA 1: Prestador / Presentación / Periodo / Quincena ─────────
        tk.Label(header, text="Prestador:", bg="#E6FFE6").grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )
        self.var_prestador = tk.StringVar(value="S.A")
        ttk.Combobox(
            header,
            textvariable=self.var_prestador,
            state="readonly",
            values=["S.A", "Otro"],
            width=15,
        ).grid(row=1, column=1, columnspan=3, padx=(2, 8), pady=(4, 0), sticky="w")

        tk.Label(header, text="Presentación:", bg="#E6FFE6").grid(
            row=1, column=4, sticky="w", pady=(4, 0)
        )
        self.var_presentacion = tk.StringVar(value="16-12-2025")
        tk.Entry(header, textvariable=self.var_presentacion, width=10).grid(
            row=1, column=5, padx=(2, 8), pady=(4, 0), sticky="w"
        )

        tk.Label(header, text="Periodo:", bg="#E6FFE6").grid(
            row=1, column=6, sticky="w", pady=(4, 0)
        )
        self.var_periodo = tk.StringVar(value="12-2025")
        ttk.Combobox(
            header,
            textvariable=self.var_periodo,
            state="readonly",
            width=8,
            values=["11-2025", "12-2025", "01-2026"],
        ).grid(row=1, column=7, padx=(2, 8), pady=(4, 0), sticky="w")

        tk.Label(header, text="Quincena:", bg="#E6FFE6").grid(
            row=1, column=8, sticky="w", pady=(4, 0)
        )
        self.var_quincena = tk.StringVar(value="1")
        tk.Spinbox(
            header,
            from_=1,
            to=2,
            width=3,
            textvariable=self.var_quincena,
        ).grid(row=1, column=9, padx=(2, 8), pady=(4, 0), sticky="w")


        tk.Label(header, text="Filtro Imágenes", bg="#E6FFE6").grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )
        self.var_filtro_img_fecha = tk.StringVar(value="04-12-2025")
        ttk.Combobox(
            header,
            textvariable=self.var_filtro_img_fecha,
            width=10,
            values=[],  # después podés llenar con fechas detectadas
        ).grid(row=2, column=1, padx=(2, 4), pady=(6, 0), sticky="w")

        tk.Button(
            header,
            text="Agregar",
            command=self._on_add_image_filter,
        ).grid(row=2, column=2, padx=(0, 12), pady=(6, 0), sticky="w")

        tk.Label(header, text="Filtro Autorizaciones", bg="#E6FFE6").grid(
            row=2, column=4, sticky="w", pady=(6, 0)
        )
        self.var_filtro_aut_fecha = tk.StringVar(value="04/12/2025")
        ttk.Combobox(
            header,
            textvariable=self.var_filtro_aut_fecha,
            width=10,
            values=[],
        ).grid(row=2, column=5, padx=(2, 4), pady=(6, 0), sticky="w")

        tk.Button(
            header,
            text="Agregar",
            command=self._on_add_authorization_filter,
        ).grid(row=2, column=6, padx=(0, 8), pady=(6, 0), sticky="w")

    def _on_new_recepcion(self):
        print("Nuevo N° recepción…")

    def _on_edit_recepcion(self):
        print("Editar recepción:", self.var_recepcion.get())

    def _on_add_image_filter(self):
        print("Aplicar filtro imágenes:", self.var_filtro_img_fecha.get())

    def _on_add_authorization_filter(self):
        print("Aplicar filtro autorizaciones:", self.var_filtro_aut_fecha.get())

    # ─────────────────────────────────────────
    # TABLAS HORIZONTALES (CON SCROLL XY)
    # ─────────────────────────────────────────
    def _build_horizontal_tables(self):
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

        container = tk.Frame(self, bg="#F0FFF0")
        container.grid(row=1, column=0, sticky="nsew")

        # Primera tabla un poco más chica que la segunda
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(0, weight=1)

        # ───── Tabla izquierda (TIF) ─────
        frame_left = tk.LabelFrame(container, text="Imágenes TIF", bg="#F0FFF0")
        frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        frame_left.columnconfigure(0, weight=1)
        frame_left.rowconfigure(0, weight=1)

        self.table_images = ttk.Treeview(
            frame_left,
            columns=("name", "date", "time"),
            show="headings",
        )

        # Headings (texto a la izquierda donde se pueda)
        self.table_images.heading("name", text="Nombre archivo", anchor="w")
        self.table_images.heading("date", text="Fecha", anchor="center")
        self.table_images.heading("time", text="Hora", anchor="center")

        # Columnas de ancho fijo (stretch=False)
        self.table_images.column("name", anchor="w")
        self.table_images.column("date", anchor="center")
        self.table_images.column("time", anchor="center")

        self.table_images.grid(row=0, column=0, sticky="nsew")

        # Scrollbars izquierda (vertical + horizontal)
        scrollbar_left_y = ttk.Scrollbar(
            frame_left, orient="vertical", command=self.table_images.yview
        )
        scrollbar_left_y.grid(row=0, column=1, sticky="ns")

        scrollbar_left_x = ttk.Scrollbar(
            frame_left, orient="horizontal", command=self.table_images.xview
        )
        scrollbar_left_x.grid(row=1, column=0, sticky="ew")

        self.table_images.configure(
            yscrollcommand=scrollbar_left_y.set,
            xscrollcommand=scrollbar_left_x.set,
        )

        # ───── Tabla derecha (IMED) ─────
        frame_right = tk.LabelFrame(container, text="Lotes / Detalles IMED", bg="#F0FFF0")
        frame_right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        frame_right.columnconfigure(0, weight=1)
        frame_right.rowconfigure(0, weight=1)

        self.table_lots = ttk.Treeview(
            frame_right,
            columns=("code", "beneficiary", "date", "reference", "amount_neto", "amount", "amount_obs"),
            show="headings",
        )

        self.table_lots.heading("code", text="Nro Receta", anchor="w")
        self.table_lots.heading("beneficiary", text="Beneficiario", anchor="w")
        self.table_lots.heading("date", text="Fecha", anchor="center")
        self.table_lots.heading("reference", text="Nro Referencia", anchor="w")
        self.table_lots.heading("amount_neto", text="Importe Neto", anchor="e")
        self.table_lots.heading("amount", text="Importe Gral", anchor="e")
        self.table_lots.heading("amount_obs", text="Importe Obs", anchor="e")

        self.table_lots.column("code", anchor="w")
        self.table_lots.column("beneficiary", anchor="w")
        self.table_lots.column("date", anchor="center")
        self.table_lots.column("reference", anchor="w",)
        self.table_lots.column("amount_neto", anchor="e")
        self.table_lots.column("amount", anchor="e")
        self.table_lots.column("amount_obs", anchor="e")

        self.table_lots.grid(row=0, column=0, sticky="nsew")

        # Scrollbars derecha (vertical + horizontal)
        scrollbar_right_y = ttk.Scrollbar(
            frame_right, orient="vertical", command=self.table_lots.yview
        )
        scrollbar_right_y.grid(row=0, column=1, sticky="ns")

        scrollbar_right_x = ttk.Scrollbar(
            frame_right, orient="horizontal", command=self.table_lots.xview
        )
        scrollbar_right_x.grid(row=1, column=0, sticky="ew")

        self.table_lots.configure(
            yscrollcommand=scrollbar_right_y.set,
            xscrollcommand=scrollbar_right_x.set,
        )

        # De momento cargo dummy; después lo podés reemplazar con list_imed_cvs
        self._populate_dummy_lots()

    # ─────────────────────────────────────────
    # CARGA DE TABLA IZQUIERDA
    # ─────────────────────────────────────────
    def _populate_images_table(self):
        for item in self.table_images.get_children():
            self.table_images.delete(item)

        for row in self.list_images_tif:
            self.table_images.insert(
                "",
                "end",
                values=(row["name"], row["date"], row["time"])
            )

    # ─────────────────────────────────────────
    # TABLA DERECHA (DUMMY POR AHORA)
    # ─────────────────────────────────────────
    def _populate_dummy_lots(self):
        recetas_por_ref = self.recetas_imed

        for item in self.table_lots.get_children():
            self.table_lots.delete(item)

        for nro_ref, receta in recetas_por_ref.items():
            self.table_lots.insert(
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

    # ─────────────────────────────────────────
    # BOTÓN → RECARGAR FILTROS
    # ─────────────────────────────────────────
    def _on_apply_filters(self):
        folder = self.var_folder.get()
        date = self.var_date.get()
        obs = self.var_obs.get()

        self.list_images_tif = self.images_handler.get_images_tif(folder, date, obs)
        self._populate_images_table()

