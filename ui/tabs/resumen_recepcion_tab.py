from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem

class ResumenRecepcionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Resumen general de Recepción (Tab)"))

        btn_refresh = QPushButton("Refrescar")
        layout.addWidget(btn_refresh)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Periodo", "Recepciones", "Estado"])
        layout.addWidget(self.table)

        btn_refresh.clicked.connect(self.refresh)

        # cargar inicial
        self.refresh()

    def refresh(self):
        # placeholder: datos fake
        data = [
            ("2025-12", "12", "OK"),
            ("2026-01", "3", "Pendiente"),
        ]

        self.table.setRowCount(len(data))
        for r, row in enumerate(data):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))


