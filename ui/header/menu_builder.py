from PySide6.QtWidgets import QMenuBar
from ui.header.actions import HeaderAction

class HeaderMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._actions_by_key: dict[str, object] = {}
    def add_group(self, group_name: str, actions: list[HeaderAction]):
        menu = self.addMenu(group_name)
        for a in actions:
            q_action = menu.addAction(a.text)
            self._actions_by_key[a.key] = q_action

    def get_action(self, key: str):
        return self._actions_by_key[key]
