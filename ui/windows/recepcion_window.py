from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QFrame, QHeaderView
)

from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService
from ui.dialogs.recepcion_create_dialog import RecepcionCreateDialog


class RecepcionesWindow(QDialog):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self.setWindowTitle("Listado Recepciones")
        self.setMinimumSize(1100, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Recepciones")
        title.setStyleSheet("font-size:16px; font-weight:600;")

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_create = QPushButton("Crear")
        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_delete.setEnabled(False)

        hl.addWidget(title)
        hl.addStretch()
        hl.addWidget(self.btn_refresh)
        hl.addWidget(self.btn_create)
        hl.addWidget(self.btn_delete)

        root.addWidget(header)

        # Tabla (SIN "Creado")
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Número Recepcion", "Obra social", "Período", "Prestador", "Estado", "Fecha recepción"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignCenter)

        root.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.open_create_dialog)
        self.btn_delete.clicked.connect(self.on_delete)
        self.table.itemSelectionChanged.connect(self._update_delete_state)

        self.load_data()

    def _update_delete_state(self):
        self.btn_delete.setEnabled(self._selected_id() is not None)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)  # Número
        if not it:
            return None
        rid = it.data(Qt.UserRole)
        return int(rid) if rid is not None else None

    def _fmt_dt(self, value) -> str:
        """Formatea datetime a 'dd/mm/yyyy HH:MM' (sin micros)."""
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y/%m/%d")
        # fallback por si viene como string ya formateado
        return str(value).split(".")[0]

    def load_data(self):
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
            it_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, it_num)

            self.table.setItem(i, 1, QTableWidgetItem(r.obra_social))
            self.table.setItem(i, 2, QTableWidgetItem(r.periodo))
            self.table.setItem(i, 3, QTableWidgetItem(r.prestador))
            self.table.setItem(i, 4, QTableWidgetItem(r.estado))

            it_fecha = QTableWidgetItem(self._fmt_dt(r.fecha_recepcion))
            it_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, it_fecha)

        self._update_delete_state()

    def open_create_dialog(self):
        dlg = RecepcionCreateDialog(self, creado_por_usuario_id=self.creado_por_usuario_id)
        if dlg.exec() == QDialog.Accepted:
            self.load_data()

    def on_delete(self):
        rid = self._selected_id()
        if not rid:
            QMessageBox.information(self, "Atención", "Seleccioná una recepción primero.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar la recepción seleccionada? (eliminación física)",
            QMessageBox.Yes | QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        try:
            with session_scope() as s:
                RecepcionService.delete(s, rid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
