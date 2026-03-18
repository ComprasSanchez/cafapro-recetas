from pathlib import Path
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.config.settings import settings
from core.version import APP_VERSION
from core.updater import apply_update, get_pending_update
from ui.dialogs.startup_status_dialog import StartupStatusDialog
from ui.main_window import MainWindow
from ui.dialogs.login_dialog import LoginDialog


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]  # raíz del proyecto


def main() -> int:
    app = QApplication(sys.argv)
    base = app_dir()
    icon_path = base / "resources" / "logo.ico"
    qss_path = base / "resources" / "style.qss"

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

        if qss_path.exists():
            app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

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
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())





