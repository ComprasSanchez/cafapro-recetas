from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)

from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService


class RecepcionPickDialog(QDialog):
    """Dialog simple para elegir una recepción existente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Elegir recepción")
        self.setMinimumSize(950, 500)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Seleccionar recepción")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        root.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Número", "Obra social", "Período", "Prestador", "Estado"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self.table)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok = QPushButton("Seleccionar")
        self.btn_ok.setEnabled(False)
        self.btn_ok.setDefault(True)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_ok)
        root.addLayout(actions)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._update_ok)

        self._load()

    def _update_ok(self):
        self.btn_ok.setEnabled(self.selected_recepcion_id() is not None)

    def _load(self):
        try:
            with session_scope() as s:
                rows = RecepcionService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar recepciones:\n{e}")
            return

        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)

            it_num = QTableWidgetItem(str(r.numero))
            it_num.setData(Qt.UserRole, r.recepcion_id)
            it_num.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, it_num)

            self.table.setItem(i, 1, QTableWidgetItem(r.obra_social))
            self.table.setItem(i, 2, QTableWidgetItem(r.periodo))
            self.table.setItem(i, 3, QTableWidgetItem(r.prestador))
            self.table.setItem(i, 4, QTableWidgetItem(r.estado))

        self._update_ok()

    def selected_recepcion_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)
        if not it:
            return None
        rid = it.data(Qt.UserRole)
        return int(rid) if rid is not None else None
