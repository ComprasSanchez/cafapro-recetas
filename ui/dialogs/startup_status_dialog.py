from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class StartupStatusDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        status: str,
        subtitle: str | None = None,
        icon_path: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setFixedWidth(460)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        head = QWidget()
        head_l = QHBoxLayout(head)
        head_l.setContentsMargins(0, 0, 0, 0)
        head_l.setSpacing(10)

        self.lb_icon = QLabel()
        self.lb_icon.setFixedSize(28, 28)
        self.lb_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if icon_path and Path(icon_path).exists():
            pix = QPixmap(str(icon_path))
            if not pix.isNull():
                self.lb_icon.setPixmap(
                    pix.scaled(
                        self.lb_icon.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

        self.lb_title = QLabel(title)
        self.lb_title.setProperty("role", "subtitle")
        self.lb_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.lb_subtitle = QLabel(subtitle or "")
        self.lb_subtitle.setObjectName("muted")
        self.lb_subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lb_subtitle.setVisible(bool(subtitle))

        title_box = QWidget()
        title_l = QVBoxLayout(title_box)
        title_l.setContentsMargins(0, 0, 0, 0)
        title_l.setSpacing(2)
        title_l.addWidget(self.lb_title)
        title_l.addWidget(self.lb_subtitle)

        head_l.addWidget(self.lb_icon, 0)
        head_l.addWidget(title_box, 1)
        root.addWidget(head)

        self.lb_status = QLabel(status)
        self.lb_status.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lb_status.setWordWrap(True)
        root.addWidget(self.lb_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        root.addWidget(self.progress)

    def set_status(self, status: str) -> None:
        self.lb_status.setText(status)
        QApplication.processEvents()

    def set_subtitle(self, subtitle: str) -> None:
        text = (subtitle or "").strip()
        self.lb_subtitle.setText(text)
        self.lb_subtitle.setVisible(bool(text))
        QApplication.processEvents()
