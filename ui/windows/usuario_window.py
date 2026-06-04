from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
    QFrame, QHeaderView
)

from ui.dialogs.usuario_create_dialog import UsuarioCreateDialog
from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class UsuariosWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Usuarios")
        self.setMinimumSize(900, 520)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Toolbar (card) =====
        toolbar = QFrame()
        toolbar.setObjectName("card")
        hl = QHBoxLayout(toolbar)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(10)

        title = QLabel("Usuarios")
        title.setProperty("role", "title")

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar…")

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")

        self.btn_toggle = QPushButton("Inactivar")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setEnabled(False)

        hl.addWidget(title)
        hl.addWidget(self.in_filter, 1)
        hl.addWidget(self.btn_refresh)
        hl.addWidget(self.btn_create)
        hl.addWidget(self.btn_toggle)

        root.addWidget(toolbar)

        # ===== Tabla (card) =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Rol", "Estado", "Últ. login"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegate(BackgroundPriorityDelegate(self.table))

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hh.setHighlightSections(False)

        tl.addWidget(self.table)
        root.addWidget(table_card, 1)

        # señales
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.open_create_dialog)
        self.btn_toggle.clicked.connect(self.on_toggle_activo)
        self.table.itemSelectionChanged.connect(self._on_selected_row_changed)
        self.in_filter.textChanged.connect(self._apply_filter)

        self.load_data()

    def _apply_filter(self, text: str) -> None:
        txt = text.strip().lower()
        for row in range(self.table.rowCount()):
            visible = not txt or any(
                txt in (self.table.item(row, c).text().lower() if self.table.item(row, c) else "")
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not visible)

    def _selected(self) -> tuple[int | None, bool | None]:
        row = self.table.currentRow()
        if row < 0:
            return None, None
        it = self.table.item(row, 0)
        if not it:
            return None, None
        uid = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        return (
            int(uid) if uid is not None else None,
            bool(activo) if activo is not None else None,
        )

    def _on_selected_row_changed(self) -> None:
        uid, activo = self._selected()
        enabled = uid is not None
        self.btn_toggle.setEnabled(enabled)
        if enabled and activo is not None:
            self.btn_toggle.setText("Inactivar" if activo else "Restaurar")
        else:
            self.btn_toggle.setText("Inactivar")

    def load_data(self) -> None:
        try:
            users = CatalogosWindowsUseCase.list_usuarios()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar usuarios:\n{e}")
            return

        self.table.setRowCount(0)

        for u in users:
            r = self.table.rowCount()
            self.table.insertRow(r)

            activo = bool(getattr(u, "activo", False))

            it_user = QTableWidgetItem(str(getattr(u, "username", "") or ""))
            it_user.setData(Qt.ItemDataRole.UserRole, getattr(u, "usuario_id", None))
            it_user.setData(Qt.ItemDataRole.UserRole + 1, activo)
            it_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 0, it_user)

            it_rol = QTableWidgetItem(str(getattr(u, "rol_descripcion", "") or ""))
            it_rol.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 1, it_rol)

            it_estado = QTableWidgetItem("Activo" if activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_estado.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if activo else warn_bg()))
            self.table.setItem(r, 2, it_estado)

            last_login = getattr(u, "ultimo_login_en", None)
            it_login = QTableWidgetItem("" if last_login is None else str(last_login))
            it_login.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, it_login)

        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText("Inactivar")

    def open_create_dialog(self) -> None:
        dlg = UsuarioCreateDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def on_toggle_activo(self) -> None:
        uid, activo = self._selected()
        if uid is None or activo is None:
            QMessageBox.information(self, "Atención", "Seleccioná un usuario primero.")
            return

        msg = "¿Marcar el usuario como INACTIVO?" if activo else "¿Restaurar (activar) el usuario seleccionado?"
        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            CatalogosWindowsUseCase.set_usuario_activo(usuario_id=uid, activo=not activo)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
