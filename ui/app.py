from pathlib import Path
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # raíz del proyecto

def main():
    app = QApplication(sys.argv)

    base = app_dir()
    icon_path = base / "resources" / "logo.ico"
    qss_path = base / "resources" / "style.qss"

    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    w = MainWindow()
    w.show()
    sys.exit(app.exec())




