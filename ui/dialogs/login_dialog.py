from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton,
    QMessageBox
)

from ui.usecase.login_usecase import LoginUseCase, AuthError


class LoginDialog(QDialog):
    MAX_ATTEMPTS = 3

    def __init__(self, parent=None):
        super().__init__(parent)

        self.attempts = 0
        self.user = None

        self.setWindowTitle("Inicio de sesión")
        self.setMinimumWidth(360)
        self.setMaximumWidth(480)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Cafapro Recetas")
        title.setAlignment(Qt.AlignCenter)
        title.setProperty("role", "title")
        root.addWidget(title)

        form = QFormLayout()

        self.in_user = QLineEdit()
        self.in_user.setPlaceholderText("Usuario")

        self.in_pass = QLineEdit()
        self.in_pass.setPlaceholderText("Contraseña")
        self.in_pass.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Usuario:", self.in_user)
        form.addRow("Contraseña:", self.in_pass)

        root.addLayout(form)

        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setProperty("variant", "primary")
        self.btn_login.setProperty("size", "md")
        self.btn_login.clicked.connect(self._on_login)

        root.addWidget(self.btn_login)

    def _on_login(self):
        username = self.in_user.text()
        password = self.in_pass.text()

        try:
            self.user = LoginUseCase.authenticate(username=username, password=password)

            self.accept()  # login OK

        except AuthError as e:
            self.attempts += 1

            QMessageBox.warning(
                self,
                "Error de autenticación",
                f"{e}\n\nIntento {self.attempts}/{self.MAX_ATTEMPTS}"
            )

            self.in_pass.clear()
            self.in_pass.setFocus()

            if self.attempts >= self.MAX_ATTEMPTS:
                QMessageBox.critical(
                    self,
                    "Acceso bloqueado",
                    "Se superó el número máximo de intentos.\nLa aplicación se cerrará."
                )
                self.reject()
