from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QDialog,
    QComboBox, QFrame, QHeaderView
)

from app.db.session import session_scope
from app.service.periodo_service import PeriodoService


MESES = [
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
]


class PeriodosWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Períodos")
        self.setMinimumSize(900, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Períodos")
        title.setStyleSheet("font-size:16px; font-weight:600;")
        root.addWidget(title)

        # ===== Panel Alta =====
        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(10)

        self.sp_anio = QSpinBox()
        self.sp_anio.setRange(2000, 2100)
        self.sp_anio.setValue(date.today().year)

        self.cb_mes = QComboBox()
        for num, nombre in MESES:
            self.cb_mes.addItem(nombre, num)
        self.cb_mes.setCurrentIndex(date.today().month - 1)

        self.cb_quincena = QComboBox()
        self.cb_quincena.addItem("1ª quincena", 1)
        self.cb_quincena.addItem("2ª quincena", 2)

        btn_refresh = QPushButton("Refrescar")
        btn_create = QPushButton("Crear")
        btn_delete = QPushButton("Eliminar seleccionado")

        card_layout.addWidget(QLabel("Año"))
        card_layout.addWidget(self.sp_anio)

        card_layout.addWidget(QLabel("Mes"))
        card_layout.addWidget(self.cb_mes)

        card_layout.addWidget(QLabel("Quincena"))
        card_layout.addWidget(self.cb_quincena)

        card_layout.addStretch()
        card_layout.addWidget(btn_refresh)
        card_layout.addWidget(btn_create)
        card_layout.addWidget(btn_delete)

        root.addWidget(card)

        # ===== Tabla (SIN ID visible) =====
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Año", "Mes", "Quincena"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self.table)

        # señales
        btn_refresh.clicked.connect(self.load_data)
        btn_create.clicked.connect(self.on_create)
        btn_delete.clicked.connect(self.on_delete)

        self.load_data()

    def _selected_periodo_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)  # año
        if not item:
            return None
        pid = item.data(Qt.ItemDataRole.UserRole)
        return int(pid) if pid is not None else None

    def load_data(self):
        with session_scope() as s:
            periodos = PeriodoService.list(s)

        self.table.setRowCount(0)

        for p in periodos:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # col 0: año (guardamos periodo_id oculto)
            it_anio = QTableWidgetItem(str(p.anio))
            it_anio.setData(Qt.ItemDataRole.UserRole, p.periodo_id)
            self.table.setItem(r, 0, it_anio)

            # col 1: mes (texto)
            mes_nombre = dict(MESES).get(p.mes, str(p.mes))
            it_mes = QTableWidgetItem(mes_nombre)
            self.table.setItem(r, 1, it_mes)

            # col 2: quincena
            it_q = QTableWidgetItem("1ª" if p.quincena == 1 else "2ª")
            self.table.setItem(r, 2, it_q)

    def on_create(self):
        anio = int(self.sp_anio.value())
        mes = int(self.cb_mes.currentData())
        quincena = int(self.cb_quincena.currentData())

        try:
            with session_scope() as s:
                PeriodoService.create(
                    s,
                    anio=anio,
                    mes=mes,
                    quincena=quincena,
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_delete(self):
        pid = self._selected_periodo_id()
        if not pid:
            QMessageBox.information(self, "Atención", "Seleccioná un período primero.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar el período seleccionado?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            with session_scope() as s:
                PeriodoService.delete(s, pid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
