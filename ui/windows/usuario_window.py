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

        # ===== Header (título + acciones) =====
        header = QFrame()
        header.setObjectName("card")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(10)

        title = QLabel("Usuarios")
        title.setStyleSheet("font-size:16px; font-weight:600;")

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_create = QPushButton("Crear")
        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_delete.setEnabled(False)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.btn_create)
        header_layout.addWidget(self.btn_delete)

        root.addWidget(header)

        # ===== Tabla (SIN ID visible) =====
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Rol", "Activo", "Últ. login"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignCenter)

        root.addWidget(self.table)

        # señales
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.open_create_dialog)
        self.btn_delete.clicked.connect(self.on_delete)

        # habilitar/deshabilitar eliminar según selección
        self.table.itemSelectionChanged.connect(self._update_delete_state)

        self.load_data()

    def _update_delete_state(self):
        self.btn_delete.setEnabled(self._selected_user_id() is not None)

    def _selected_user_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)  # username
        if not item:
            return None
        uid = item.data(Qt.UserRole)
        return int(uid) if uid is not None else None

    def load_data(self):
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
            it_user = QTableWidgetItem(u.username)
            it_user.setData(Qt.UserRole, u.usuario_id)
            self.table.setItem(r, 0, it_user)

            # col 1: rol
            it_rol = QTableWidgetItem(u.rol_descripcion)
            self.table.setItem(r, 1, it_rol)

            # col 2: activo (más prolijo: Sí/No)
            it_activo = QTableWidgetItem("Sí" if u.activo else "No")
            it_activo.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, it_activo)

            # col 3: último login
            it_login = QTableWidgetItem("" if u.ultimo_login_en is None else str(u.ultimo_login_en))
            self.table.setItem(r, 3, it_login)

        self._update_delete_state()

    def open_create_dialog(self):
        dlg = UsuarioCreateDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def on_delete(self):
        uid = self._selected_user_id()
        if not uid:
            QMessageBox.information(self, "Atención", "Seleccioná un usuario primero.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar el usuario seleccionado? (eliminación física)",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        try:
            with session_scope() as s:
                UsuariosService.delete(s, uid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
