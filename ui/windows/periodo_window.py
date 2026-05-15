from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSpinBox, QMessageBox, QDialog,
    QComboBox, QFrame, QHeaderView, QLineEdit
)

from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


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
        self.setWindowState(Qt.WindowState.WindowMaximized)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== form_card =====
        form_card = QFrame()
        form_card.setObjectName("card")
        form_l = QVBoxLayout(form_card)
        form_l.setContentsMargins(16, 16, 16, 16)
        form_l.setSpacing(12)

        # header row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        title = QLabel("Períodos")
        title.setProperty("role", "title")
        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.btn_refresh)
        form_l.addLayout(header_row)

        # field_grid
        field_grid = QGridLayout()
        field_grid.setHorizontalSpacing(12)
        field_grid.setVerticalSpacing(8)
        field_grid.setColumnStretch(1, 1)
        field_grid.setColumnStretch(3, 1)

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

        # Row 0: Año | sp_anio | Mes | cb_mes
        field_grid.addWidget(QLabel("Año"), 0, 0)
        field_grid.addWidget(self.sp_anio, 0, 1)
        field_grid.addWidget(QLabel("Mes"), 0, 2)
        field_grid.addWidget(self.cb_mes, 0, 3)

        # Row 1: Quincena | cb_quincena
        field_grid.addWidget(QLabel("Quincena"), 1, 0)
        field_grid.addWidget(self.cb_quincena, 1, 1)

        form_l.addLayout(field_grid)

        # actions row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar en tabla…")

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")

        self.btn_toggle = QPushButton("Eliminar")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setEnabled(False)

        actions_row.addWidget(self.in_filter, 1)
        actions_row.addWidget(self.btn_create)
        actions_row.addWidget(self.btn_toggle)
        form_l.addLayout(actions_row)

        root.addWidget(form_card)

        # ===== table_card =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Año", "Mes", "Quincena", "Estado"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegate(BackgroundPriorityDelegate(self.table))

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
        self.in_filter.textChanged.connect(self._apply_filter)

        self.load_data()

    # ---------------- filter ----------------
    def _apply_filter(self, text: str) -> None:
        txt = text.strip().lower()
        for row in range(self.table.rowCount()):
            visible = not txt or any(
                txt in (self.table.item(row, c).text().lower() if self.table.item(row, c) else "")
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not visible)

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
            periodos = CatalogosWindowsUseCase.list_periodos(solo_activos=False)
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
            it_estado.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if p.activo else warn_bg()))
            self.table.setItem(r, 3, it_estado)

        self._update_action_state()

    # ---------------- actions ----------------
    def on_create(self) -> None:
        anio = int(self.sp_anio.value())
        mes = int(self.cb_mes.currentData())
        quincena = int(self.cb_quincena.currentData())

        try:
            CatalogosWindowsUseCase.create_periodo(
                anio=anio,
                mes=mes,
                quincena=quincena,
            )
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
            CatalogosWindowsUseCase.set_periodo_activo(
                periodo_id=int(pid),
                activo=not bool(activo),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
