from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QWidget, QMessageBox

from ui.jobs.jobs_service import ServiceJob


class BaseTabWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._runner = QThreadPool(self)
        self._runner.setMaxThreadCount(1)  # cola serial
        self._active_jobs: set[ServiceJob] = set()
        self._active_job_keys: dict[str, ServiceJob] = {}
        self.footer_channel = self.__class__.__name__.lower()

    def _footer(self):
        w = self.window()
        return getattr(w, "footer", None)

    def footer_set(self, *, status: str | None = None, info: str | None = None, loading: bool | None = None):
        f = self._footer()
        if not f:
            return

        channel = str(getattr(self, "footer_channel", self.__class__.__name__.lower()) or "general")

        if loading:
            f.start_loading(status or "Cargando…", channel=channel)
        elif loading is False:
            f.stop_loading(status or "OK", channel=channel)
        else:
            if status is not None:
                f.set_status(status, channel=channel)

        if info is not None:
            f.set_info(info, channel=channel)

    def run_job(
        self,
        fn: Callable[..., Any],
        *args: Any,
        title: str = "Cargando…",
        on_result: Callable[[Any], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_finished: Callable[[], None] | None = None,
        job_key: str | None = None,
        **kwargs: Any,
    ) -> None:
        key = str(job_key or "").strip()
        if key and key in self._active_job_keys:
            self.footer_set(info="Ya hay una operación en curso para esta acción.")
            return

        job = ServiceJob(fn, *args, title=title, **kwargs)

        self._active_jobs.add(job)
        if key:
            self._active_job_keys[key] = job

        def _cleanup():
            self._active_jobs.discard(job)
            if key and self._active_job_keys.get(key) is job:
                self._active_job_keys.pop(key, None)
        # ✅ prende loading al empezar
        job.signals.started.connect(lambda msg: self.footer_set(status=msg, loading=True))
        job.signals.finished.connect(lambda msg: (_cleanup(), _finished(msg)))
        job.signals.error.connect( lambda err: (_cleanup(), _error(err)))

        def _progress(_p: int, msg: str):
            if msg:
                self.footer_set(info=msg)

        job.signals.progress.connect(_progress)

        if on_result:
            job.signals.result.connect(on_result)

        def _error(err_text: str):
            self.footer_set(status="Error", info="", loading=False)

            msg = err_text.lower()

            is_not_found = (
                    "filenotfounderror" in msg
                    or "no se encontró el archivo imed" in msg
                    or "no se encontro el archivo imed" in msg
                    or "no such file or directory" in msg
            )

            if on_error:
                on_error(err_text)
                return

            if is_not_found:
                nice = _extract_last_line(err_text)  # te dejo helper abajo
                QMessageBox.warning(self, "Archivo no encontrado", nice)
            else:
                QMessageBox.critical(self, "Error", err_text)

        def _extract_last_line(tb: str) -> str:
            lines = [l.strip() for l in tb.splitlines() if l.strip()]
            return lines[-1] if lines else tb

        def _finished(_msg: str):
            self.footer_set(status="OK", loading=False)
            if on_finished:
                on_finished()


        self._runner.start(job)
