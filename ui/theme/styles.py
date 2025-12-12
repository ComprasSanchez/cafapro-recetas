from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.theme.colors import (
    BG_APP,
    BG_PANEL,
    BG_CARD,
    BG_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

def apply_theme(root: tk.Misc | None = None) -> None:
    """Aplica estilos globales (TTK + defaults) con look desktop prolijo.

    - En Windows intenta 'vista' para look nativo.
    - En otros sistemas usa 'clam' (más consistente para estilos).
    """
    style = ttk.Style(master=root)

    # Elegir theme (desktop)
    for candidate in ("vista", "xpnative", "clam"):
        try:
            style.theme_use(candidate)
            break
        except tk.TclError:
            continue

    # Fuente base
    style.configure(".", font=("Segoe UI", 9))

    # Frames / Labels por defecto
    style.configure("TFrame", background=BG_APP)
    style.configure("TLabel", background=BG_APP, foreground=TEXT_PRIMARY)

    # Panel (header / filtros)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT_PRIMARY)

    # Card (contenedores)
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("Card.TLabel", background=BG_CARD, foreground=TEXT_PRIMARY)

    # Buttons (dejamos look desktop; solo padding)
    style.configure("TButton", padding=(10, 4))
    style.configure("Primary.TButton", padding=(12, 4), font=("Segoe UI", 9, "bold"))

    # Entries / Combobox
    style.configure("TEntry", padding=(6, 3))
    style.configure("TCombobox", padding=(6, 3))

    # Separators
    style.configure("TSeparator", background=BG_BORDER)

    # Treeview (tablas)
    style.configure(
        "Treeview",
        background=BG_CARD,
        fieldbackground=BG_CARD,
        foreground=TEXT_PRIMARY,
        rowheight=24,
        bordercolor=BG_BORDER,
        lightcolor=BG_BORDER,
        darkcolor=BG_BORDER,
        relief="flat",
    )
    style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    # Selección (suave)
    style.map(
        "Treeview",
        background=[("selected", "#CFE8FF")],
        foreground=[("selected", TEXT_PRIMARY)],
    )
