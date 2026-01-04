from ui.header.actions import HeaderAction
from ui.window_manager import WindowManager

class HeaderController:
    def __init__(self, main_window, tabs_manager, window_manager: WindowManager):
        self.main_window = main_window
        self.tabs = tabs_manager
        self.windows = window_manager

    def handle(self, action: HeaderAction):
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
