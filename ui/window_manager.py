from PySide6.QtWidgets import QWidget

class WindowManager:
    def __init__(self):
        self._cache: dict[str, QWidget] = {}

    def open(self, key: str, factory):
        w = self._cache.get(key)
        if w is None:
            w = factory()
            self._cache[key] = w

        w.show()
        w.raise_()
        w.activateWindow()
        return w
