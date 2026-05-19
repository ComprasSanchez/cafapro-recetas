"""
Status background colors for table rows and cells.
Returns theme-appropriate QColor so every table looks consistent.
"""
from __future__ import annotations

from PySide6.QtGui import QColor


def _c(light: str, dark: str) -> QColor:
    from ui.theme.theme_manager import theme_manager
    return QColor(dark if theme_manager.is_dark() else light)


# ── Semantic palette ───────────────────────────────────────────────────────────
#   Light: pastel tints  |  Dark: medium jewel tones (level-700 for visibility)
#   Pair each bg with its fg for guaranteed contrast on both themes.

def ok_bg() -> QColor:
    """Auditada sin débitos, importe oficial, troquel encontrado."""
    return _c("#D1FAE5", "#15803d")   # light: mint pastel | dark: green-700

def ok_fg() -> QColor:
    return _c("#064e3b", "#d1fae5")   # light: dark green | dark: light mint

def warn_bg() -> QColor:
    """Auditada con débitos, troquel no encontrado."""
    return _c("#FEF3C7", "#b45309")   # light: amber pastel | dark: amber-700

def warn_fg() -> QColor:
    return _c("#78350f", "#fef3c7")   # light: dark amber | dark: light amber

def error_bg() -> QColor:
    """Diferencia de montos, troquel con discrepancia."""
    return _c("#FEE2E2", "#b91c1c")   # light: red pastel | dark: red-700

def error_fg() -> QColor:
    return _c("#7f1d1d", "#fee2e2")   # light: dark red | dark: light pink

def outline_color() -> QColor:
    """Color del borde de fila activa en AuditoriaTab (visible en ambos temas)."""
    return QColor(99, 102, 241)   # indigo-500
