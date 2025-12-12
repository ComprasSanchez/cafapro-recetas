import tkinter as tk
from tkinter import ttk

from ui.theme.colors import BG_PANEL

class LotsFiltersPanel(tk.Frame):
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, bg=BG_PANEL, padx=10, pady=8, **kwargs)
        self.controller = controller

        self._setup_style()

        # vars UI
        self.var_recepcion = tk.StringVar(value="")
        self.var_obra_social = tk.StringVar(value="PAMI")
        self.var_prestador = tk.StringVar(value="S.A")
        self.var_presentacion = tk.StringVar(value="16-12-2025")
        self.var_periodo = tk.StringVar(value="12-2025")
        self.var_quincena = tk.StringVar(value="1")

        self.var_filtro_img_fecha = tk.StringVar(value="04-12-2025")
        self.var_filtro_aut_fecha = tk.StringVar(value="04/12/2025")

        self._build()

    def _setup_style(self):
        style = ttk.Style()

        # Si querés un look más moderno, probá con "clam" (suele verse mejor)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", font=("Segoe UI", 9))
        style.configure("Filters.TLabel", font=("Segoe UI", 9))
        style.configure("Filters.TEntry", padding=(6, 3))
        style.configure("Filters.TCombobox", padding=(6, 3))
        style.configure("Filters.TButton", padding=(10, 4))
        style.configure("Filters.Primary.TButton", padding=(12, 4), font=("Segoe UI", 9, "bold"))

        style.map(
            "Filters.Primary.TButton",
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )

    def _build(self):
        # Grid prolijo
        for c in range(0, 12):
            self.grid_columnconfigure(c, pad=6)
        self.grid_columnconfigure(11, weight=1)

        # Wrapper ttk (mejor spacing)
        content = tk.Frame(self, bg=BG_PANEL)
        content.grid(row=0, column=0, sticky="ew")
        content.grid_columnconfigure(11, weight=1)

        # Helpers
        def label(text, r, c):
            ttk.Label(content, text=text, style="Filters.TLabel").grid(
                row=r, column=c, sticky="e", padx=(0, 6), pady=3
            )

        def sep(r):
            ttk.Separator(content, orient="horizontal").grid(
                row=r, column=0, columnspan=12, sticky="ew", pady=(6, 6)
            )

        # ========== FILA 0 ==========
        label("N° Recepción", 0, 0)
        ttk.Entry(content, textvariable=self.var_recepcion, width=10, style="Filters.TEntry").grid(
            row=0, column=1, sticky="w", pady=3
        )

        ttk.Button(content, text="+", width=3, style="Filters.TButton", command=self._on_new_recepcion).grid(
            row=0, column=2, sticky="w", pady=3
        )
        ttk.Button(content, text="✎", width=3, style="Filters.TButton", command=self._on_edit_recepcion).grid(
            row=0, column=3, sticky="w", pady=3
        )

        label("Obra social", 0, 4)
        ttk.Entry(content, textvariable=self.var_obra_social, width=18, style="Filters.TEntry").grid(
            row=0, column=5, sticky="w", pady=3
        )

        # ========== FILA 1 ==========
        label("Prestador", 1, 0)
        ttk.Combobox(
            content,
            textvariable=self.var_prestador,
            state="readonly",
            values=["S.A", "Otro"],
            width=18,
            style="Filters.TCombobox",
        ).grid(row=1, column=1, columnspan=3, sticky="w", pady=3)

        label("Presentación", 1, 4)
        ttk.Entry(content, textvariable=self.var_presentacion, width=12, style="Filters.TEntry").grid(
            row=1, column=5, sticky="w", pady=3
        )

        label("Periodo", 1, 6)
        ttk.Combobox(
            content,
            textvariable=self.var_periodo,
            state="readonly",
            values=["11-2025", "12-2025", "01-2026"],
            width=10,
            style="Filters.TCombobox",
        ).grid(row=1, column=7, sticky="w", pady=3)

        label("Quincena", 1, 8)
        ttk.Spinbox(content, from_=1, to=2, width=5, textvariable=self.var_quincena).grid(
            row=1, column=9, sticky="w", pady=3
        )

        sep(2)

        # ========== FILA 3 ==========
        # Bloque filtros
        ttk.Label(content, text="Filtros", font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=(0, 4)
        )

        label("Imágenes", 4, 0)
        ttk.Combobox(content, textvariable=self.var_filtro_img_fecha, width=12, values=[], style="Filters.TCombobox").grid(
            row=4, column=1, sticky="w", pady=3
        )
        ttk.Button(content, text="Agregar", style="Filters.TButton", command=self._on_add_image_filter).grid(
            row=4, column=2, columnspan=2, sticky="w", pady=3
        )

        label("Autorizaciones", 4, 4)
        ttk.Combobox(content, textvariable=self.var_filtro_aut_fecha, width=12, values=[], style="Filters.TCombobox").grid(
            row=4, column=5, sticky="w", pady=3
        )
        ttk.Button(content, text="Agregar", style="Filters.TButton", command=self._on_add_authorization_filter).grid(
            row=4, column=6, columnspan=2, sticky="w", pady=3
        )

        # Botón principal a la derecha
        ttk.Button(content, text="Aplicar filtros", style="Filters.Primary.TButton", command=self._on_apply).grid(
            row=4, column=10, sticky="e", pady=3
        )

    def _sync_filters_to_controller(self):
        self.controller.set_filter(
            recepcion=self.var_recepcion.get(),
            obra_social=self.var_obra_social.get(),
            prestador=self.var_prestador.get(),
            presentacion=self.var_presentacion.get(),
            periodo=self.var_periodo.get(),
            quincena=self.var_quincena.get(),
            filtro_img_fecha=self.var_filtro_img_fecha.get(),
            filtro_aut_fecha=self.var_filtro_aut_fecha.get(),
        )

    def _on_apply(self):
        self._sync_filters_to_controller()
        self.controller.apply_filters()

    def _on_new_recepcion(self):
        self._sync_filters_to_controller()
        print("Nuevo N° recepción…")

    def _on_edit_recepcion(self):
        self._sync_filters_to_controller()
        print("Editar recepción:", self.var_recepcion.get())

    def _on_add_image_filter(self):
        self._sync_filters_to_controller()
        self.controller.apply_filters()

    def _on_add_authorization_filter(self):
        self._sync_filters_to_controller()
        self.controller.apply_filters()
