import re
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme.colors import BG_PANEL, BG_CARD, BG_BORDER, TEXT_PRIMARY, TEXT_SECONDARY


class FiltersPanel(tk.Frame):
    """Panel de filtros de Lotes.

    - Metadata (solo lectura): obra social, prestador, presentación, periodo, quincena
    - Filtros editables: recepción, fecha imágenes, fecha autorizaciones

    Las fechas se fuerzan a DD/MM/YYYY al salir del campo o al aplicar.
    """

    def __init__(self, master, controller, **kwargs):
        super().__init__(master, bg=BG_PANEL, padx=10, pady=8, **kwargs)
        self.controller = controller

        # Vars UI
        self.var_recepcion = tk.StringVar(value="")

        # Metadata (SOLO LECTURA: viene de otro componente)
        self.var_obra_social = tk.StringVar(value="PAMI")
        self.var_prestador = tk.StringVar(value="S.A")
        self.var_presentacion = tk.StringVar(value="")
        self.var_periodo = tk.StringVar(value="")
        self.var_quincena = tk.StringVar(value="")

        # Filtros (EDITABLES)
        hoy = datetime.now().strftime("%d/%m/%Y")
        self.var_filtro_img_fecha = tk.StringVar(value=hoy)
        self.var_filtro_aut_fecha = tk.StringVar(value=hoy)

        self._build()

    # ─────────────────────────────────────────
    # API pública: cargar metadata desde afuera
    # ─────────────────────────────────────────
    def set_meta(
        self,
        *,
        prestador: str | None = None,
        obra_social: str | None = None,
        presentacion: str | None = None,
        periodo: str | None = None,
        quincena: str | int | None = None,
    ):
        if prestador is not None:
            self.var_prestador.set(prestador)
        if obra_social is not None:
            self.var_obra_social.set(obra_social)
        if presentacion is not None:
            self.var_presentacion.set(presentacion)
        if periodo is not None:
            self.var_periodo.set(periodo)
        if quincena is not None:
            self.var_quincena.set(str(quincena))

    def _build(self):
        # grid base
        for c in range(0, 12):
            self.grid_columnconfigure(c, pad=6)
        self.grid_columnconfigure(11, weight=1)

        content = ttk.Frame(self, style="Panel.TFrame")
        content.grid(row=0, column=0, sticky="ew")
        content.grid_columnconfigure(11, weight=1)

        def label(text, r, column):
            ttk.Label(content, text=text, style="Panel.TLabel").grid(
                row=r, column=column, sticky="e", padx=(3, 4), pady=3
            )

        def section_title(text, r):
            tk.Label(
                content,
                text=text,
                bg=BG_PANEL,
                fg=TEXT_PRIMARY,
                font=("Segoe UI", 9, "bold"),
            ).grid(row=r, column=0, sticky="w", pady=(4, 2))

        def ro_value(var: tk.StringVar, r: int, column: int, width: int = 16):
            """Chip/valor de solo lectura (look desktop)."""
            tk.Label(
                content,
                textvariable=var,
                bg=BG_CARD,
                fg=TEXT_PRIMARY,
                bd=1,
                relief="solid",
                highlightthickness=1,
                highlightbackground=BG_BORDER,
                padx=8,
                pady=3,
                width=width,
                anchor="w",
            ).grid(row=r, column=column, sticky="w", pady=3)

        # ───────── Row 0 ─────────
        label("N° Recepción", 0, 0)
        ttk.Entry(content, textvariable=self.var_recepcion, width=10).grid(
            row=0, column=1, sticky="w", pady=3
        )

        ttk.Button(content, text="+", width=3, command=self._on_new_recepcion).grid(
            row=0, column=2, sticky="w", pady=3
        )
        ttk.Button(content, text="✎", width=3, command=self._on_edit_recepcion).grid(
            row=0, column=3, sticky="w", pady=3
        )

        label("Obra social", 0, 4)
        ro_value(self.var_obra_social, 0, 5, width=18)

        # ───────── Row 1 (metadata readonly) ─────────
        label("Prestador", 1, 0)
        ro_value(self.var_prestador, 1, 1, width=18)

        label("Presentación", 1, 4)
        ro_value(self.var_presentacion, 1, 5, width=12)

        label("Periodo", 1, 6)
        ro_value(self.var_periodo, 1, 7, width=10)

        label("Quincena", 1, 8)
        ro_value(self.var_quincena, 1, 9, width=6)

        # Divider
        ttk.Separator(content, orient="horizontal").grid(
            row=2, column=0, columnspan=12, sticky="ew", pady=(6, 6)
        )

        # ───────── Filters row ─────────
        section_title("Filtros", 3)

        label("Filtro Imágenes", 4, 0)
        self.entry_img_fecha = ttk.Entry(content, textvariable=self.var_filtro_img_fecha, width=12)
        self.entry_img_fecha.grid(row=4, column=1, sticky="w", pady=3, padx=3)

        ttk.Button(content, text="Agregar", command=self._on_add_image_filter).grid(
            row=4, column=2, columnspan=2, sticky="w", pady=3
        )

        label("Autorizaciones", 4, 4)
        self.entry_aut_fecha = ttk.Entry(content, textvariable=self.var_filtro_aut_fecha, width=12)
        self.entry_aut_fecha.grid(row=4, column=5, sticky="w", pady=3, padx=3)

        ttk.Button(content, text="Agregar", command=self._on_add_authorization_filter).grid(
            row=4, column=6, columnspan=2, sticky="w", pady=3
        )

        # Hint (muy suave)
        tk.Label(
            content,
            text="Formato: DD/MM/YYYY",
            bg=BG_PANEL,
            fg=TEXT_SECONDARY,
            font=("Segoe UI", 8),
        ).grid(row=4, column=8, sticky="w", pady=3)

        # Validación/normalización de fechas
        self._wire_date_entry(self.var_filtro_img_fecha, self.entry_img_fecha)
        self._wire_date_entry(self.var_filtro_aut_fecha, self.entry_aut_fecha)

        # Primary action right
        ttk.Button(
            content,
            text="Procesar",
            style="Primary.TButton",
            command=self.controller.process_tif
        ).grid(row=4, column=10, sticky="e", pady=3)

    # ─────────────────────────────────────────
    # Date helpers
    # ─────────────────────────────────────────
    @staticmethod
    def _normalize_date(raw: str) -> str | None:
        """Normaliza a DD/MM/YYYY.

        Acepta:
        - 04122025
        - 04/12/2025
        - 04-12-2025

        Retorna:
        - "" si viene vacío
        - "DD/MM/YYYY" si es válida
        - None si es inválida
        """
        raw = (raw or "").strip()
        if raw == "":
            return ""

        raw = raw.replace("-", "/")

        # Si ya viene con /, validamos formato básico
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):
            candidate = raw
        else:
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) != 8:
                return None
            candidate = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"

        # Validación de fecha real
        try:
            datetime.strptime(candidate, "%d/%m/%Y")
        except ValueError:
            return None

        return candidate

    def _wire_date_entry(self, var: tk.StringVar, entry: ttk.Entry) -> None:
        """Permite tipear estable y normaliza al salir."""

        def validate_key(proposed: str) -> bool:
            # Permitimos números, / y - (para pegar "04-12-2025")
            if proposed == "":
                return True
            if len(proposed) > 10:
                return False
            return re.fullmatch(r"[0-9/\-]*", proposed) is not None

        vcmd = (self.register(validate_key), "%P")
        entry.configure(validate="key", validatecommand=vcmd)

        def on_focus_out(_evt):
            val = var.get()
            normalized = self._normalize_date(val)
            if normalized is None:
                messagebox.showwarning("Fecha inválida", "Usá DD/MM/YYYY (ej: 04/12/2025).")
                var.set("")
                entry.focus_set()
                entry.selection_range(0, tk.END)
                return
            var.set(normalized)

        entry.bind("<FocusOut>", on_focus_out)

    # ─────────────────────────────────────────
    # Sync de filtros
    # ─────────────────────────────────────────
    def _sync_filters_to_controller(self) -> bool:
        img = self._normalize_date(self.var_filtro_img_fecha.get())
        if img is None:
            messagebox.showwarning("Fecha inválida", "Fecha de Imágenes inválida. Usá DD/MM/YYYY (ej: 04/12/2025).")
            self.entry_img_fecha.focus_set()
            self.entry_img_fecha.selection_range(0, tk.END)
            return False

        aut = self._normalize_date(self.var_filtro_aut_fecha.get())
        if aut is None:
            messagebox.showwarning("Fecha inválida", "Fecha de Autorizaciones inválida. Usá DD/MM/YYYY (ej: 04/12/2025).")
            self.entry_aut_fecha.focus_set()
            self.entry_aut_fecha.selection_range(0, tk.END)
            return False

        # reflejar normalizado
        self.var_filtro_img_fecha.set(img)
        self.var_filtro_aut_fecha.set(aut)

        # solo lo editable acá
        self.controller.set_filter(
            recepcion=self.var_recepcion.get().strip(),
            filtro_img_fecha=img,
            filtro_aut_fecha=aut,
        )
        return True

    # ─────────────────────────────────────────
    # Handlers
    # ─────────────────────────────────────────

    def _on_new_recepcion(self):
        self._sync_filters_to_controller()
        print("Nuevo N° recepción…")

    def _on_edit_recepcion(self):
        self._sync_filters_to_controller()
        print("Editar recepción:", self.var_recepcion.get())

    def _on_add_image_filter(self):
        if not self._sync_filters_to_controller():
            return
        self.controller.reload_images()

    def _on_add_authorization_filter(self):
        if not self._sync_filters_to_controller():
            return
        self.controller.reload_imed()
