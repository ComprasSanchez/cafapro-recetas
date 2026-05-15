from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

LIGHT = "light"
DARK = "dark"


class ThemeManager:
    def __init__(self) -> None:
        self._settings = QSettings("Cafapro", "CafaproRecetas")
        self._current: str = str(self._settings.value("ui/theme", LIGHT))
        self._base: Path = self._resolve_base()

    def _resolve_base(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    @property
    def current(self) -> str:
        return self._current

    def is_dark(self) -> bool:
        return self._current == DARK

    def apply(self, theme: str | None = None) -> None:
        if theme is not None:
            self._current = theme
        qss_file = self._base / "resources" / f"style_{self._current}.qss"
        app = QApplication.instance()
        if app and qss_file.exists():
            app.setStyleSheet(qss_file.read_text(encoding="utf-8"))
        self._settings.setValue("ui/theme", self._current)

    def toggle(self) -> None:
        self.apply(DARK if self._current == LIGHT else LIGHT)


theme_manager = ThemeManager()
