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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lb = QLabel("Número de receta:")
        layout.addWidget(lb)

        self.in_receta = QLineEdit()

        # solo números
        regex = QRegularExpression(r"[0-9]+")
        validator = QRegularExpressionValidator(regex)
        self.in_receta.setValidator(validator)

        layout.addWidget(self.in_receta)

        btns = QHBoxLayout()
        btns.setSpacing(8)

        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.setProperty("size", "md")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Confirmar")
        btn_ok.setProperty("variant", "primary")
        btn_ok.setProperty("size", "md")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)

        btns.addStretch(1)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)

        layout.addLayout(btns)
        self.in_receta.setFocus()

    def numero_receta(self) -> str:
        return (self.in_receta.text() or "").strip()