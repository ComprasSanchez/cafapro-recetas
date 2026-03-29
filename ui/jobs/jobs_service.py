from __future__ import annotations

import inspect
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class WorkerSignals(QObject):
    started = Signal(str)                 # mensaje
    finished = Signal(str)                # mensaje
    result = Signal(object)               # cualquier cosa
    error = Signal(str)                   # texto de error (stack)
    progress = Signal(int, str)           # (0..100, mensaje opcional)


@dataclass
class JobContext:
    """Contexto que puede usar el service para reportar progreso/cancelación."""
    emit_progress: Callable[[int, str], None]


class ServiceJob(QRunnable):
    """
    Ejecuta una función (service) en background.
    La función puede recibir opcionalmente un 'ctx' para progress.
    """
    def __init__(
        self,
        fn: Callable[..., Any],
        *args: Any,
        title: str = "Cargando…",
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.title = title
        self.signals = WorkerSignals()

        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        self.signals.started.emit(self.title)

        try:
            # opcional: si el service acepta ctx, se lo pasamos
            ctx = JobContext(
                emit_progress=lambda p, m="": self.signals.progress.emit(int(p), m or "")
            )

            if _supports_ctx(self.fn):
                result = self.fn(*self.args, ctx=ctx, **self.kwargs)
            else:
                result = self.fn(*self.args, **self.kwargs)

            self.signals.result.emit(result)

        except Exception:
            self.signals.error.emit(traceback.format_exc())

        finally:
            self.signals.finished.emit("Listo")


def _supports_ctx(fn: Callable[..., Any]) -> bool:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False

    if "ctx" in sig.parameters:
        return True

    for p in sig.parameters.values():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            return True

    return False
