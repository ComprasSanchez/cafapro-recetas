from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QLabel


class ImageViewer(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(False)

        self._pix_original: QPixmap | None = None
        self._zoom: float = 1.0

    def set_pixmap(self, pix: QPixmap | None) -> None:
        self._pix_original = pix
        self._zoom = 1.0
        self._apply_zoom()

    def zoom_reset(self) -> None:
        self._zoom = 1.0
        self._apply_zoom()

    def zoom_in(self) -> None:
        self._zoom = min(self._zoom * 1.15, 8.0)
        self._apply_zoom()

    def zoom_out(self) -> None:
        self._zoom = max(self._zoom / 1.15, 0.10)
        self._apply_zoom()

    def fit_to(self, viewport_size: QSize) -> None:
        if not self._pix_original or self._pix_original.isNull():
            return
        pw = self._pix_original.width()
        ph = self._pix_original.height()
        vw = max(1, viewport_size.width() - 10)
        vh = max(1, viewport_size.height() - 10)
        self._zoom = min(vw / pw, vh / ph)
        self._zoom = max(self._zoom, 0.01)
        self._apply_zoom()

    def wheelEvent(self, event: QWheelEvent) -> None:
        # Ctrl + rueda => zoom
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return

        event.ignore()

    def _apply_zoom(self) -> None:
        if not self._pix_original or self._pix_original.isNull():
            self.setPixmap(QPixmap())
            return

        scaled = self._pix_original.scaled(
            int(self._pix_original.width() * self._zoom),
            int(self._pix_original.height() * self._zoom),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.resize(scaled.size())

