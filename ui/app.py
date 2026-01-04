import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("public/logo.ico"))
    qss_path = Path(__file__).parent / "styles" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    w = MainWindow()
    w.show()
    sys.exit(app.exec())

