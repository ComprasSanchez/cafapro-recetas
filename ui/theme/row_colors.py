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
#   Light: pastel tints  |  Dark: deep jewel tones
#   Text color is intentionally left to the global QSS so it auto-adapts.

def ok_bg() -> QColor:
    """Auditada sin débitos, importe oficial, troquel encontrado."""
    return _c("#D1FAE5", "#166534")   # light: mint pastel | dark: green-800

def warn_bg() -> QColor:
    """Auditada con débitos, troquel no encontrado."""
    return _c("#FEF3C7", "#92400E")   # light: amber pastel | dark: amber-800

def error_bg() -> QColor:
    """Diferencia de montos, troquel con discrepancia."""
    return _c("#FEE2E2", "#991B1B")   # light: red pastel | dark: red-800

def outline_color() -> QColor:
    """Color del borde de fila activa en AuditoriaTab (visible en ambos temas)."""
    return QColor(99, 102, 241)   # indigo-500
