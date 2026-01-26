from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar
from PySide6.QtCore import Qt

class FooterManeger(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.lb_status = QLabel("Listo")
        self.lb_info = QLabel("")
        self.lb_info.setAlignment(Qt.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(140)
        self.progress.setRange(0, 0)      # modo indeterminado
        self.progress.setVisible(False)

        self.addWidget(self.lb_status, 1)
        self.addWidget(self.lb_info, 2)
        self.addPermanentWidget(self.progress)

    # ---- API pública ----
    def set_status(self, text: str):
        self.lb_status.setText(text)

    def set_info(self, text: str):
        self.lb_info.setText(text)

    def start_loading(self, text: str = "Cargando…"):
        self.set_status(text)
        self.progress.setVisible(True)

    def stop_loading(self, text: str = "Listo"):
        self.set_status(text)
        self.progress.setVisible(False)
