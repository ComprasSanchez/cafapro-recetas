from PySide6.QtGui import QResizeEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QSizePolicy

class FooterManeger(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._status_full = "Listo"
        self._info_full = ""

        self.lb_status = QLabel("Listo")
        self.lb_info = QLabel("")
        self.lb_info.setAlignment(Qt.AlignCenter)
        self.lb_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lb_info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lb_status.setMinimumWidth(0)
        self.lb_info.setMinimumWidth(0)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(120)
        self.progress.setRange(0, 0)      # modo indeterminado
        self.progress.setVisible(False)

        self.addWidget(self.lb_status, 1)
        self.addWidget(self.lb_info, 2)
        self.addPermanentWidget(self.progress)

    # ---- API pública ----
    def set_status(self, text: str):
        self._status_full = str(text or "")
        self._refresh_elided_texts()

    def set_info(self, text: str):
        self._info_full = str(text or "")
        self._refresh_elided_texts()

    def start_loading(self, text: str = "Cargando…"):
        self.set_status(text)
        self.progress.setVisible(True)

    def stop_loading(self, text: str = "Listo"):
        self.set_status(text)
        self.progress.setVisible(False)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_elided_texts()

    def _refresh_elided_texts(self) -> None:
        self._set_elided(self.lb_status, self._status_full)
        self._set_elided(self.lb_info, self._info_full)

    @staticmethod
    def _set_elided(label: QLabel, text: str) -> None:
        txt = str(text or "")
        width = max(10, int(label.contentsRect().width()))
        elided = label.fontMetrics().elidedText(txt, Qt.TextElideMode.ElideRight, width)
        label.setText(elided)
        label.setToolTip(txt if elided != txt else "")
