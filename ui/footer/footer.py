from PySide6.QtGui import QResizeEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QSizePolicy


class FooterManeger(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._states: dict[str, dict[str, object]] = {}
        self._active_channel = "general"
        self._status_full = ""
        self._info_full = ""

        self.lb_status = QLabel("Listo")
        self.lb_info = QLabel("")
        self.lb_info.setAlignment(Qt.AlignCenter)
        self.lb_status.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        self.lb_info.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.lb_status.setMinimumWidth(0)
        self.lb_status.setMaximumWidth(180)
        self.lb_info.setMinimumWidth(0)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(120)
        self.progress.setRange(0, 0)      # modo indeterminado
        self.progress.setVisible(False)

        self.addWidget(self.lb_status, 0)
        self.addWidget(self.lb_info, 5)
        self.addPermanentWidget(self.progress)

        self._ensure_state(self._active_channel)
        self._refresh_from_active_state()

    def set_active_channel(self, channel: str) -> None:
        channel_name = str(channel or "general")
        self._active_channel = channel_name
        self._ensure_state(channel_name)
        self._refresh_from_active_state()

    # ---- API pública ----
    def set_status(self, text: str, *, channel: str | None = None):
        state = self._ensure_state(channel)
        state["status"] = str(text or "")
        self._refresh_if_active(channel)

    def set_info(self, text: str, *, channel: str | None = None):
        state = self._ensure_state(channel)
        state["info"] = str(text or "")
        self._refresh_if_active(channel)

    def start_loading(self, text: str = "Cargando…", *, channel: str | None = None):
        state = self._ensure_state(channel)
        state["status"] = str(text or "Cargando…")
        state["loading"] = True
        self._refresh_if_active(channel)

    def stop_loading(self, text: str = "OK", *, channel: str | None = None):
        state = self._ensure_state(channel)
        state["status"] = str(text or "OK")
        state["loading"] = False
        self._refresh_if_active(channel)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._refresh_elided_texts()

    def _ensure_state(self, channel: str | None) -> dict[str, object]:
        name = str(channel or self._active_channel or "general")
        if name not in self._states:
            self._states[name] = {
                "status": "Listo",
                "info": "",
                "loading": False,
            }
        return self._states[name]

    def _refresh_if_active(self, channel: str | None) -> None:
        name = str(channel or self._active_channel or "general")
        if name != self._active_channel:
            return
        self._refresh_from_active_state()

    def _refresh_from_active_state(self) -> None:
        state = self._ensure_state(self._active_channel)
        self._status_full = str(state.get("status", "") or "")
        self._info_full = str(state.get("info", "") or "")
        self.progress.setVisible(bool(state.get("loading", False)))
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
