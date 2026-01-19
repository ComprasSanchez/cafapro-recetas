from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog,
    QFrame, QHeaderView
)

from app.db.session import session_scope
from app.service.usuario_service import UsuariosService
from ui.dialogs.usuario_create_dialog import UsuarioCreateDialog


class UsuariosWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Usuarios")
        self.setMinimumSize(900, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Header (card) =====
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Usuarios")
        title.setProperty("role", "title")

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        self.btn_refresh.setMinimumHeight(32)

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")
        self.btn_create.setMinimumHeight(32)

        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_delete.setProperty("variant", "ghost")
        self.btn_delete.setMinimumHeight(32)
        self.btn_delete.setEnabled(False)

        hl.addWidget(title)
        hl.addStretch(1)
        hl.addWidget(self.btn_refresh)
        hl.addWidget(self.btn_create)
        hl.addWidget(self.btn_delete)

        root.addWidget(header)

        # ===== Tabla (card) =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Rol", "Activo", "Últ. login"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hh.setHighlightSections(False)

        tl.addWidget(self.table, 1)
        root.addWidget(table_card, 1)

        # señales
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.open_create_dialog)
        self.btn_delete.clicked.connect(self.on_delete)
        self.table.itemSelectionChanged.connect(self._update_delete_state)

        self.load_data()

    def _update_delete_state(self) -> None:
        self.btn_delete.setEnabled(self._selected_user_id() is not None)

    def _selected_user_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)  # username
        if not item:
            return None
        uid = item.data(Qt.ItemDataRole.UserRole)
        return int(uid) if uid is not None else None

    def load_data(self) -> None:
        try:
            with session_scope() as s:
                users = UsuariosService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar usuarios:\n{e}")
            return

        self.table.setRowCount(0)

        for u in users:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # col 0: username (guardamos usuario_id oculto)
            it_user = QTableWidgetItem(str(getattr(u, "username", "") or ""))
            it_user.setData(Qt.ItemDataRole.UserRole, getattr(u, "usuario_id", None))
            it_user.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 0, it_user)

            # col 1: rol
            it_rol = QTableWidgetItem(str(getattr(u, "rol_descripcion", "") or ""))
            it_rol.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(r, 1, it_rol)

            # col 2: activo
            it_activo = QTableWidgetItem("Sí" if bool(getattr(u, "activo", False)) else "No")
            it_activo.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, it_activo)

            # col 3: último login
            last_login = getattr(u, "ultimo_login_en", None)
            it_login = QTableWidgetItem("" if last_login is None else str(last_login))
            it_login.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, it_login)

        self._update_delete_state()

    def open_create_dialog(self) -> None:
        dlg = UsuarioCreateDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def on_delete(self) -> None:
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.information(self, "Atención", "Seleccioná un usuario primero.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar el usuario seleccionado? (eliminación física)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            with session_scope() as s:
                UsuariosService.delete(s, uid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
