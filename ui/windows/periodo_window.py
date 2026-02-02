from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QDialog,
    QComboBox, QFrame, QHeaderView
)

from app.db.session import session_scope
from app.service.catalogos.periodo_service import PeriodoService


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

        # ===== Header (card) =====
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Períodos")
        title.setProperty("role", "title")
        hl.addWidget(title)
        hl.addStretch(1)

        root.addWidget(header)

        # ===== Panel Alta (card) =====
        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(10)

        self.sp_anio = QSpinBox()
        self.sp_anio.setRange(2000, 2100)
        self.sp_anio.setValue(date.today().year)
        self.sp_anio.setMinimumHeight(28)
        self.sp_anio.setFixedWidth(110)

        self.cb_mes = QComboBox()
        self.cb_mes.setMinimumHeight(28)
        self.cb_mes.setMinimumWidth(160)
        for num, nombre in MESES:
            self.cb_mes.addItem(nombre, num)
        self.cb_mes.setCurrentIndex(date.today().month - 1)

        self.cb_quincena = QComboBox()
        self.cb_quincena.setMinimumHeight(28)
        self.cb_quincena.setMinimumWidth(160)
        self.cb_quincena.addItem("1ª quincena", 1)
        self.cb_quincena.addItem("2ª quincena", 2)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        self.btn_refresh.setMinimumHeight(32)

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")
        self.btn_create.setMinimumHeight(32)

        self.btn_toggle = QPushButton("Eliminar")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setMinimumHeight(32)
        self.btn_toggle.setEnabled(False)

        card_layout.addWidget(QLabel("Año"))
        card_layout.addWidget(self.sp_anio)
        card_layout.addWidget(QLabel("Mes"))
        card_layout.addWidget(self.cb_mes)
        card_layout.addWidget(QLabel("Quincena"))
        card_layout.addWidget(self.cb_quincena)
        card_layout.addStretch(1)
        card_layout.addWidget(self.btn_refresh)
        card_layout.addWidget(self.btn_create)
        card_layout.addWidget(self.btn_toggle)

        root.addWidget(card)

        # ===== Tabla (card) =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Año", "Mes", "Quincena", "Estado"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hh.setHighlightSections(False)

        tl.addWidget(self.table, 1)
        root.addWidget(table_card, 1)

        # señales
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.on_create)
        self.btn_toggle.clicked.connect(self.on_toggle_activo)
        self.table.itemSelectionChanged.connect(self._update_action_state)

        self.load_data()

    # ---------------- selection helpers ----------------
    def _selected(self) -> tuple[int | None, bool | None]:
        row = self.table.currentRow()
        if row < 0:
            return None, None

        it = self.table.item(row, 0)  # Año (guardamos metadata acá)
        if not it:
            return None, None

        pid = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        return (int(pid) if pid is not None else None, bool(activo) if activo is not None else None)

    def _update_action_state(self) -> None:
        pid, activo = self._selected()
        if pid is None or activo is None:
            self.btn_toggle.setEnabled(False)
            self.btn_toggle.setText("Eliminar")
            return

        self.btn_toggle.setEnabled(True)
        self.btn_toggle.setText("Eliminar" if activo else "Restaurar")

    # ---------------- data ----------------
    def load_data(self) -> None:
        try:
            with session_scope() as s:
                periodos = PeriodoService.list(s, solo_activos=False)  # ✅ trae todo
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar períodos:\n{e}")
            return

        self.table.setRowCount(0)

        meses_map = dict(MESES)

        for p in periodos:
            r = self.table.rowCount()
            self.table.insertRow(r)

            # col 0: año (guardamos periodo_id + activo)
            it_anio = QTableWidgetItem(str(p.anio))
            it_anio.setData(Qt.ItemDataRole.UserRole, p.periodo_id)
            it_anio.setData(Qt.ItemDataRole.UserRole + 1, p.activo)
            it_anio.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, it_anio)

            # col 1: mes
            it_mes = QTableWidgetItem(meses_map.get(p.mes, str(p.mes)))
            it_mes.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, it_mes)

            # col 2: quincena
            it_q = QTableWidgetItem("1ª" if p.quincena == 1 else "2ª")
            it_q.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, it_q)

            # col 3: estado
            it_estado = QTableWidgetItem("Activo" if p.activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 3, it_estado)

        self._update_action_state()

    # ---------------- actions ----------------
    def on_create(self) -> None:
        anio = int(self.sp_anio.value())
        mes = int(self.cb_mes.currentData())
        quincena = int(self.cb_quincena.currentData())

        try:
            with session_scope() as s:
                PeriodoService.create(s, anio=anio, mes=mes, quincena=quincena)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_toggle_activo(self) -> None:
        pid, activo = self._selected()
        if not pid:
            QMessageBox.information(self, "Atención", "Seleccioná un período primero.")
            return

        if activo:
            msg = "¿Marcar el período como INACTIVO?"
            action_text = "Inactivar"
        else:
            msg = "¿Restaurar (activar) el período seleccionado?"
            action_text = "Activar"

        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            with session_scope() as s:
                if activo:
                    PeriodoService.delete_logico(s, pid)
                else:
                    PeriodoService.restore(s, pid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
