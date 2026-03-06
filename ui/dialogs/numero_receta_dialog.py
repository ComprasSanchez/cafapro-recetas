from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton
)


class NumeroRecetaDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Ingresar Numero Receta")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        lb = QLabel("Número de receta:")
        layout.addWidget(lb)

        self.in_receta = QLineEdit()

        # 🔹 SOLO NÚMEROS
        regex = QRegularExpression(r"[0-9]+")
        validator = QRegularExpressionValidator(regex)
        self.in_receta.setValidator(validator)

        layout.addWidget(self.in_receta)

        btns = QHBoxLayout()

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirmar")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)

        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        layout.addLayout(btns)
        self.in_receta.setFocus()

    def numero_receta(self) -> str:
        return (self.in_receta.text() or "").strip()