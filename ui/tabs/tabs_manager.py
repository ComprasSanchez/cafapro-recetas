from PySide6.QtWidgets import QTabWidget

from ui.tabs.carga_recepcion_tab import CargaRecepcionTab
from ui.tabs.resumen_recepcion_tab import ResumenRecepcionTab

class TabsManager(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.removeTab)

        self._index_by_key: dict[str, int] = {}

    def open_tab(self, key: str):
        # si ya está abierto → foco
        if key in self._index_by_key:
            self.setCurrentIndex(self._index_by_key[key])
            return

        widget, title = self._create_tab(key)
        idx = self.addTab(widget, title)
        self.setCurrentIndex(idx)
        self._index_by_key[key] = idx

        # si se cierra, limpiar mapa
        def _on_close(i):
            if i == idx:
                self._index_by_key.pop(key, None)

        self.tabCloseRequested.connect(_on_close)

    def _create_tab(self, key: str):
        if key == "resumen_recepcion":
            return ResumenRecepcionTab(self), "Resumen Recepción"
        if key == "carga-recepcion-handler":
            return CargaRecepcionTab(self), "Carga Recepcion"

        raise KeyError(f"Tab no registrada: {key}")
