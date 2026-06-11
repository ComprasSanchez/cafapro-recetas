from pathlib import Path
import logging
import sys
import threading
import traceback
from datetime import datetime

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config.settings import settings
from core.api_client import close_client
from core.version import APP_VERSION
from core.updater import apply_update, get_pending_update
from ui.dialogs.startup_status_dialog import StartupStatusDialog
from ui.main_window import MainWindow
from ui.dialogs.login_dialog import LoginDialog
from ui.theme.theme_manager import theme_manager

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    if getattr(sys, "frozen", False):
        log_dir = Path.home() / "Documents" / "CafaproRecetas" / "logs"
    else:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"cafapro_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    logging.getLogger("crash_logger").info(
        "=== Sesión iniciada — %s | log: %s ===", datetime.now().isoformat(), log_file
    )


def _show_crash_dialog(msg: str) -> bool:
    """Muestra error con opción de continuar. Retorna True si el usuario elige continuar."""
    try:
        if QApplication.instance() is None:
            return False
        mb = QMessageBox()
        mb.setWindowTitle("Error inesperado")
        mb.setText(
            "Ocurrió un error inesperado.\n\n"
            "Podés intentar continuar usando la aplicación o cerrarla."
        )
        mb.setDetailedText(msg)
        mb.setIcon(QMessageBox.Icon.Critical)
        continuar_btn = mb.addButton("Continuar", QMessageBox.ButtonRole.AcceptRole)
        mb.addButton("Cerrar aplicación", QMessageBox.ButtonRole.RejectRole)
        mb.exec()
        return mb.clickedButton() is continuar_btn
    except Exception:
        return False


def _install_global_exception_handlers() -> None:
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        log.critical("Excepción no capturada (hilo principal):\n%s", msg)
        if not _show_crash_dialog(msg):
            sys.exit(1)

    sys.excepthook = _excepthook

    def _thread_excepthook(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is SystemExit:
            return
        msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_tb))
        log.critical(
            "Excepción no capturada (hilo %r):\n%s",
            getattr(args.thread, "name", args.thread),
            msg,
        )

    threading.excepthook = _thread_excepthook


class SafeApplication(QApplication):
    """QApplication que atrapa excepciones en el event loop de Qt para evitar cierres sorpresivos."""

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            log.critical(
                "Excepción en Qt notify (receiver=%r, event=%r):",
                receiver,
                event,
                exc_info=True,
            )
            return False


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # raíz del proyecto


def main() -> int:
    _setup_logging()
    _install_global_exception_handlers()
    log.info("Arrancando Cafapro Recetas %s", APP_VERSION)

    app = SafeApplication(sys.argv)
    base = app_dir()
    icon_path = base / "resources" / "logo.ico"

    update_info = get_pending_update()
    if update_info:
        do_update = bool(update_info.mandatory)

        if not update_info.mandatory:
            reply = QMessageBox.question(
                None,
                "Actualización disponible",
                f"Hay una nueva versión ({update_info.latest_version}).\n\n¿Desea actualizar ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            do_update = reply == QMessageBox.StandardButton.Yes

        if do_update:
            update_dlg = StartupStatusDialog(
                title="Actualización",
                status="Preparando actualización…",
                subtitle=f"Versión actual: {APP_VERSION}",
                icon_path=icon_path,
            )
            update_dlg.show()
            QApplication.processEvents()

            try:
                apply_update(update_info, status_cb=update_dlg.set_status)
            except Exception as e:
                update_dlg.close()
                QMessageBox.warning(
                    None,
                    "Actualización",
                    f"No se pudo completar la actualización automática.\n\n{e}",
                )
            else:
                update_dlg.close()

    init_dlg = StartupStatusDialog(
        title="Inicialización",
        status="Iniciando aplicación…",
        subtitle=f"Cafapro Recetas {APP_VERSION}",
        icon_path=icon_path,
    )
    init_dlg.show()
    QApplication.processEvents()

    try:
        init_dlg.set_status("Validando configuración…")
        settings.validate_required()

        init_dlg.set_status("Cargando recursos visuales…")
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))

        theme_manager.apply()

        init_dlg.set_status("Preparando inicio de sesión…")
    except Exception as e:
        init_dlg.close()
        QMessageBox.critical(
            None,
            "Error de inicialización",
            str(e),
        )
        return 1
    finally:
        init_dlg.close()

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return 0

    w = MainWindow(current_user=login.user)
    w.showMaximized()

    try:
        exit_code = app.exec()
        log.info("App cerrada normalmente (código %d)", exit_code)
        return exit_code
    except Exception:
        log.critical("Excepción en el event loop de Qt:", exc_info=True)
        return 1
    finally:
        close_client()


if __name__ == "__main__":
    raise SystemExit(main())





