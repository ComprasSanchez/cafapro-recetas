from PySide6.QtWidgets import QMessageBox

from ui.header.actions import HeaderAction
from ui.security.permissions import can_access_header_action
from ui.window_manager import WindowManager

class HeaderController:
    def __init__(self, main_window, tabs_manager, window_manager: WindowManager):
        self.main_window = main_window
        self.tabs = tabs_manager
        self.windows = window_manager

    def handle(self, action: HeaderAction):
        if not can_access_header_action(
            user=getattr(self.main_window, "current_user", None),
            action_key=action.key,
            kind=action.kind,
            tab_key=action.tab_key,
        ):
            QMessageBox.warning(
                self.main_window,
                "Sin permisos",
                "No tenés permisos para acceder a esta opción.",
            )
            return

        if action.kind == "tab":
            if not action.tab_key:
                raise ValueError(f"Action {action.key} es tab pero no tiene tab_key")
            self.tabs.open_tab(action.tab_key)
            return

        if action.kind == "window":
            if not action.window_factory:
                raise ValueError(f"Action {action.key} es window pero no tiene window_factory")
            self.windows.open(action.key, action.window_factory)
            return

        if action.kind == "callback":
            if not action.callback:
                raise ValueError(f"Action {action.key} es callback pero no tiene callback")
            action.callback()
            return

        raise ValueError(f"Tipo de acción desconocido: {action.kind}")
