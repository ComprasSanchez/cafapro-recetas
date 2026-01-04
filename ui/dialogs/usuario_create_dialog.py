from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QMessageBox
)

from app.db.session import session_scope
from app.service.rol_service import RolesService
from app.service.usuario_service import UsuariosService


class UsuarioCreateDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear usuario")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._build_ui()
        self._load_roles()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Nuevo usuario")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        root.addWidget(title)

        form = QFormLayout()
        self.in_username = QLineEdit()
        self.in_username.setPlaceholderText("username")

        self.in_password = QLineEdit()
        self.in_password.setPlaceholderText("password")
        self.in_password.setEchoMode(QLineEdit.EchoMode.Password)

        self.in_password2 = QLineEdit()
        self.in_password2.setPlaceholderText("repetir password")
        self.in_password2.setEchoMode(QLineEdit.EchoMode.Password)

        self.cb_rol = QComboBox()

        form.addRow("Username", self.in_username)
        form.addRow("Password", self.in_password)
        form.addRow("Repetir", self.in_password2)
        form.addRow("Rol", self.cb_rol)

        root.addLayout(form)

        # botones
        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok = QPushButton("Crear")

        self.btn_ok.setDefault(True)  # Enter = crear
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_ok)

        root.addLayout(actions)

        # signals
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_create)
        self.in_password2.returnPressed.connect(self._on_create)

    def _load_roles(self):
        self.cb_rol.clear()
        try:
            with session_scope() as s:
                roles = RolesService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar roles:\n{e}")
            self.cb_rol.addItem("Error cargando roles", None)
            self.cb_rol.setEnabled(False)
            return

        if not roles:
            self.cb_rol.addItem("No hay roles", None)
            self.cb_rol.setEnabled(False)
            return

        self.cb_rol.setEnabled(True)
        for r in roles:
            self.cb_rol.addItem(r.descripcion, r.rol_id)

    def _on_create(self):
        username = self.in_username.text().strip()
        p1 = self.in_password.text()
        p2 = self.in_password2.text()
        rol_id = self.cb_rol.currentData()

        if rol_id is None:
            QMessageBox.information(self, "Atención", "Seleccioná un rol primero.")
            return

        if not username:
            QMessageBox.information(self, "Atención", "Username es obligatorio.")
            return

        if len(p1) < 6:
            QMessageBox.information(self, "Atención", "La contraseña debe tener al menos 6 caracteres.")
            return

        if p1 != p2:
            QMessageBox.information(self, "Atención", "Las contraseñas no coinciden.")
            return

        try:
            with session_scope() as s:
                UsuariosService.create(
                    s,
                    username=username,
                    password=p1,
                    rol_id=int(rol_id),
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.accept()
