from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QMenu
)

from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.motivos_debitos_usecase import MotivosDebitosUseCase


class MotivosDebitosWindow(QDialog):
    ROW_H = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motivos de Débito")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        self._build_ui()
        self._load_data()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # -------- form_card --------
        form_card = QFrame()
        form_card.setObjectName("card")
        form_l = QVBoxLayout(form_card)
        form_l.setContentsMargins(16, 16, 16, 16)
        form_l.setSpacing(12)

        # header row
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        title = QLabel("Motivos de Débito")
        title.setProperty("role", "title")
        header_row.addWidget(title)
        header_row.addStretch(1)
        form_l.addLayout(header_row)

        # field_grid
        field_grid = QGridLayout()
        field_grid.setHorizontalSpacing(12)
        field_grid.setVerticalSpacing(8)
        field_grid.setColumnStretch(1, 1)
        field_grid.setColumnStretch(3, 1)

        self.in_descripcion = QLineEdit()
        self.in_descripcion.setPlaceholderText("Descripción")

        self.cb_lado = QComboBox()
        self.cb_lado.addItem("Frente", "F")
        self.cb_lado.addItem("Dorso", "D")

        # Row 0: Descripción | in_descripcion | Lado | cb_lado
        field_grid.addWidget(QLabel("Descripción"), 0, 0)
        field_grid.addWidget(self.in_descripcion, 0, 1)
        field_grid.addWidget(QLabel("Lado"), 0, 2)
        field_grid.addWidget(self.cb_lado, 0, 3)

        form_l.addLayout(field_grid)

        # actions row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar en tabla…")

        self.btn_add = QPushButton("Agregar")
        self.btn_add.setProperty("variant", "primary")

        self.btn_toggle = QPushButton("Dar de baja")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setEnabled(False)

        actions_row.addWidget(self.in_filter, 1)
        actions_row.addWidget(self.btn_add)
        actions_row.addWidget(self.btn_toggle)
        form_l.addLayout(actions_row)

        root.addWidget(form_card, 0)

        # -------- table_card --------
        table_card = QFrame()
        table_card.setObjectName("card")
        table_l = QVBoxLayout(table_card)
        table_l.setContentsMargins(12, 12, 12, 12)
        table_l.setSpacing(0)

        self.tbl = QTableWidget(0, 3)
        self.tbl.setHorizontalHeaderLabels([
            "Descripción",
            "Lado",
            "Activo",
        ])

        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tbl.setItemDelegate(BackgroundPriorityDelegate(self.tbl))
        self.tbl.customContextMenuRequested.connect(self._on_context_menu)

        table_l.addWidget(self.tbl, 1)
        root.addWidget(table_card, 1)

        # señales
        self.btn_add.clicked.connect(self._create)
        self.btn_toggle.clicked.connect(self._toggle_selected)
        self.tbl.itemSelectionChanged.connect(self._update_toggle_state)
        self.in_filter.textChanged.connect(self._apply_filter)

    # ---------------- filter ----------------
    def _apply_filter(self, text: str) -> None:
        txt = text.strip().lower()
        for row in range(self.tbl.rowCount()):
            visible = not txt or any(
                txt in (self.tbl.item(row, c).text().lower() if self.tbl.item(row, c) else "")
                for c in range(self.tbl.columnCount())
            )
            self.tbl.setRowHidden(row, not visible)

    # ---------------- toggle state ----------------
    def _update_toggle_state(self) -> None:
        row = self.tbl.currentRow()
        has_sel = row >= 0 and self.tbl.item(row, 0) is not None
        self.btn_toggle.setEnabled(has_sel)
        if has_sel:
            activo = self.tbl.item(row, 2).text() == "Sí" if self.tbl.item(row, 2) else True
            self.btn_toggle.setText("Dar de baja" if activo else "Activar")

    def _toggle_selected(self) -> None:
        row = self.tbl.currentRow()
        if row < 0:
            return
        it = self.tbl.item(row, 0)
        if not it:
            return
        mid = it.data(Qt.UserRole)
        if mid is not None:
            self._toggle(int(mid))

    # ---------------- CREATE ----------------
    def _create(self):
        desc = (self.in_descripcion.text() or "").strip()
        lado = self.cb_lado.currentData()

        if not desc:
            QMessageBox.warning(self, "Falta dato", "La descripción es obligatoria.")
            return

        try:
            MotivosDebitosUseCase.create_motivo(
                descripcion=desc,
                lado=lado,
            )

            self.in_descripcion.clear()
            self._load_data()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------------- LOAD ----------------
    def _load_data(self):
        rows = MotivosDebitosUseCase.list_motivos()

        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.tbl.setRowHeight(i, self.ROW_H)

            self._set_item(i, 0, r.descripcion)
            self._set_item(i, 1, r.lado)

            activo_txt = "Sí" if r.activo else "No"
            it_activo = QTableWidgetItem(activo_txt)
            it_activo.setFlags(it_activo.flags() & ~Qt.ItemIsEditable)
            it_activo.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if r.activo else warn_bg()))
            self.tbl.setItem(i, 2, it_activo)

            it = QTableWidgetItem(r.descripcion)
            it.setData(Qt.UserRole, r.motivo_debito_id)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(i, 0, it)

        self._update_toggle_state()

    # ---------------- TOGGLE BAJA LÓGICA ----------------
    def _toggle(self, motivo_id: int):
        try:
            MotivosDebitosUseCase.toggle_activo(motivo_id=motivo_id)
            self._load_data()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------------- Utils ----------------
    def _set_item(self, row, col, text):
        it = QTableWidgetItem(str(text))
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.tbl.setItem(row, col, it)

    def _on_context_menu(self, pos):
        row = self.tbl.rowAt(pos.y())
        if row < 0:
            return

        motivo_id = self.tbl.item(row, 0).data(Qt.UserRole)
        activo_txt = self.tbl.item(row, 2).text()

        menu = QMenu(self)

        if activo_txt == "Sí":
            menu.addAction("Dar de baja")
        else:
            menu.addAction("Activar")

        chosen = menu.exec(self.tbl.viewport().mapToGlobal(pos))
        if not chosen:
            return

        self._toggle(motivo_id)
