import tkinter as tk
from ui.theme.colors import BG_PANEL, BG_CARD
class Main(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg="#DDDDDD")

        # ───────── Layout interno de Main ─────────
        self.rowconfigure(0, weight=0)  # barra de pestañas
        self.rowconfigure(1, weight=1)  # contenido
        self.columnconfigure(0, weight=1)

        # Barra de pestañas
        self.tab_bar = tk.Frame(self, bg=BG_PANEL, height=28)
        self.tab_bar.grid(row=0, column=0, sticky="ew")
        self.tab_bar.grid_propagate(False)

        # Contenedor de páginas (frames)
        self.content = tk.Frame(self, bg=BG_CARD)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)

        # Estado interno
        self.pages = {}    # nombre -> frame de página
        self.tabs = {}     # nombre -> frame de pestaña
        self.current = None

    # =============== API PÚBLICA ===============

    def open_page(self, name: str, page_class: type[tk.Frame]):
        """
        Abre una pestaña con una página.
        Si ya existe, simplemente la enfoca.
        """
        # Si ya está abierta, solo la muestro
        if name in self.pages:
            self.show_page(name)
            return

        # 1) Crear el frame de la página
        page = page_class(self.content)
        page.grid(row=0, column=0, sticky="nsew")

        # 2) Crear la pestaña visual
        tab = self._create_tab(name)

        # 3) Guardar en los diccionarios
        self.pages[name] = page
        self.tabs[name] = tab

        # 4) Mostrarla
        self.show_page(name)

    def show_page(self, name: str):
        """Muestra la página/pestaña indicada."""
        if name not in self.pages:
            return

        # Quitar selección visual de la pestaña anterior
        if self.current and self.current in self.tabs:
            old_tab = self.tabs[self.current]
            old_tab.config(bg=BG_PANEL)
            for child in old_tab.winfo_children():
                child.config(bg=BG_PANEL)

        # Levantar el frame de la página
        self.pages[name].tkraise()

        # Marcar pestaña como activa
        new_tab = self.tabs[name]
        new_tab.config(bg=BG_CARD)
        for child in new_tab.winfo_children():
            child.config(bg=BG_CARD)

        self.current = name

    def close_page(self, name: str):
        """Cierra la pestaña y destruye su contenido."""
        if name not in self.pages:
            return

        # Destruir widgets
        self.pages[name].destroy()
        self.tabs[name].destroy()

        # Quitarlos de los diccionarios
        del self.pages[name]
        del self.tabs[name]

        # Si cerré la actual, elegir otra
        if self.current == name:
            self.current = None
            if self.pages:
                # muestro la última que quede
                last_name = list(self.pages.keys())[-1]
                self.show_page(last_name)

    # =============== Helpers internos ===============

    def _create_tab(self, name: str) -> tk.Frame:
        """Crea la pestañita (nombre + botón cerrar) en la barra."""
        tab = tk.Frame(self.tab_bar, bg=BG_PANEL, bd=1, relief="solid")
        tab.pack(side="left", padx=(0, 1))

        lbl = tk.Label(tab, text=name, bg=BG_PANEL, padx=8, pady=3)
        lbl.pack(side="left")

        btn = tk.Button(
            tab,
            text="✕",
            bg=BG_PANEL,
            relief="flat",
            padx=4,
            command=lambda n=name: self.close_page(n),
        )
        btn.pack(side="right")

        # Click sobre la pestaña cambia a esa página
        tab.bind("<Button-1>", lambda e, n=name: self.show_page(n))
        lbl.bind("<Button-1>", lambda e, n=name: self.show_page(n))

        return tab

