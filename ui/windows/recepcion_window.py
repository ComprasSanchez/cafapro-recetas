from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame
)

class RecepcionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recepción - Crear/Editar")
        self.setMinimumSize(760, 420)

        root = QVBoxLayout(self)

        card = QFrame()
        card.setObjectName("card")
        root.addWidget(card)

        layout = QVBoxLayout(card)

        title_row = QHBoxLayout()
        title = QLabel("Listado Recepciones")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        title_row.addWidget(title)
        title_row.addStretch()

        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        title_row.addWidget(btn_close)
        layout.addLayout(title_row)

        layout.addWidget(QLabel("ID / Nro Recepción"))

        row = QHBoxLayout()
        self.txt_id = QLineEdit()
        self.txt_id.setPlaceholderText("Ej: 12345")
        row.addWidget(self.txt_id)

        btn_load = QPushButton("Cargar")
        btn_new = QPushButton("Nueva")
        row.addWidget(btn_load)
        row.addWidget(btn_new)
        layout.addLayout(row)

        layout.addWidget(QLabel("Acá va el formulario..."))

        footer = QHBoxLayout()
        footer.addStretch()
        btn_save = QPushButton("Guardar")
        btn_save.setProperty("variant", "primary")  # usa QSS variant
        footer.addWidget(btn_save)
        layout.addLayout(footer)

        btn_new.clicked.connect(self._on_new)
        btn_load.clicked.connect(self._on_load)
        btn_save.clicked.connect(self._on_save)

    def _on_new(self):
        self.txt_id.setText("")

    def _on_load(self):
        rid = self.txt_id.text().strip()
        # cargar recepción por rid

    def _on_save(self):
        # guardar
        pass
