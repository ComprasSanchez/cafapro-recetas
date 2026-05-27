"""
Crash logger: configura sys.excepthook y logging a archivo.
Llamar setup_crash_logger() lo antes posible al arrancar la app.
"""
from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _log_dir() -> Path:
    """Directorio de logs: Documentos\CafaproRecetas\logs en producción, carpeta logs/ en dev."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Documents" / "CafaproRecetas" / "logs"
    return Path(__file__).parents[1] / "logs"


def setup_crash_logger(log_dir: Path | None = None) -> Path:
    """
    Configura logging a archivo y captura excepciones no manejadas.
    Retorna la ruta del archivo de log activo.
    """
    base = log_dir or _log_dir()
    base.mkdir(parents=True, exist_ok=True)

    log_file = base / f"cafapro_{datetime.now():%Y%m%d}.log"

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    logger = logging.getLogger("crash_logger")
    logger.info("=== Sesión iniciada — %s ===", datetime.now().isoformat())
    logger.info("Log file: %s", log_file)

    # ---- excepthook global ----
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.critical("Excepción no capturada:\n%s", msg)

    sys.excepthook = _excepthook

    return log_file
