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

        self.tabs = TabsManager(current_user, self)
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.footer = FooterManeger(self)
        self.setStatusBar(self.footer)

        self.window_manager = WindowManager()
        self.header_controller = HeaderController(
            main_window=self,
            tabs_manager=self.tabs,
            window_manager=self.window_manager
        )

        self._setup_header(current_user)
        self._on_tab_changed(self.tabs.currentIndex())

    def _setup_header(self, current_user):
        actions_by_group = build_header_actions(self, current_user)

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

    def _on_tab_changed(self, index: int) -> None:
        tab = self.tabs.widget(index) if index >= 0 else None
        channel = getattr(tab, "footer_channel", "general") if tab is not None else "general"
        self.footer.set_active_channel(str(channel or "general"))

