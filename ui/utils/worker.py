from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool


class WorkerSignals(QObject):
    finished = Signal(object)   # resultado
    error = Signal(str)         # texto de error


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], **kwargs):
        super().__init__()
        self.fn = fn
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            out = self.fn(**self.kwargs)
            self.signals.finished.emit(out)
        except Exception:
            self.signals.error.emit(traceback.format_exc())
