from PySide6.QtWidgets import QMainWindow

from ui.footer.footer import FooterManeger
from ui.tabs.tabs_manager import TabsManager
from ui.window_manager import WindowManager
from ui.header.menu_builder import HeaderMenuBar
from ui.header.registry import build_header_actions
from ui.header.controller import HeaderController

class MainWindow(QMainWindow):
    def __init__(self, current_user):
        super().__init__()

        self.current_user = current_user

        # ---- UI NORMAL ----
        self.setWindowTitle("Cafapro Recetas")
        self.showMaximized()

        self.tabs = TabsManager(self)
        self.setCentralWidget(self.tabs)

        self.footer = FooterManeger(self)
        self.setStatusBar(self.footer)

        self.window_manager = WindowManager()
        self.header_controller = HeaderController(
            main_window=self,
            tabs_manager=self.tabs,
            window_manager=self.window_manager
        )

        self._setup_header()

    def _setup_header(self):
        actions_by_group = build_header_actions(self)

        menubar = HeaderMenuBar(self)
        self.setMenuBar(menubar)

        for group, actions in actions_by_group.items():
            menubar.add_group(group, actions)

        for actions in actions_by_group.values():
            for a in actions:
                qaction = menubar.get_action(a.key)
                qaction.triggered.connect(
                    lambda checked=False, _a=a: self.header_controller.handle(_a)
                )

