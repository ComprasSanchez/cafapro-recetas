from PySide6.QtWidgets import QMessageBox, QTabWidget

from ui.security.permissions import can_access_tab
from ui.tabs.archivo_cvs_tab import ArchivoCvsTab
from ui.tabs.auditoria_tab import AuditoriaTab
from ui.tabs.carga_recepcion_tab import CargaRecepcionTab

class TabsManager(QTabWidget):
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.removeTab)
        self.current_user = current_user

        self._index_by_key: dict[str, int] = {}

    def open_tab(self, key: str):
        if not can_access_tab(user=self.current_user, tab_key=key):
            QMessageBox.warning(
                self,
                "Sin permisos",
                "No tenés permisos para acceder a esta pestaña.",
            )
            return

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
        if key == "carga-recepcion-handler":
            return CargaRecepcionTab(
                creado_por_usuario_id=self.current_user.usuario_id,
                current_user=self.current_user,
                parent=self,
            ), "Carga de recepción"
        if key == "archivo-cvs":
            return ArchivoCvsTab(self), "Archivo CSV"
        if key == "auditoria":
            return AuditoriaTab(
                self,
                creado_por_usuario_id=self.current_user.usuario_id,
                current_user=self.current_user,
            ), "Auditoría"

        raise KeyError(f"Tab no registrada: {key}")
