from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit, QSizePolicy
)

from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class PrestadoresWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prestadores")
        self.setMinimumSize(1050, 580)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Form card (header + fields + actions) =====
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        # --- Header row ---
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        title = QLabel("Prestadores")
        title.setProperty("role", "title")
        header_row.addWidget(title)
        header_row.addStretch(1)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        header_row.addWidget(self.btn_refresh)

        form_layout.addLayout(header_row)

        # --- Field grid ---
        field_grid = QGridLayout()
        field_grid.setHorizontalSpacing(12)
        field_grid.setVerticalSpacing(8)
        field_grid.setColumnStretch(1, 1)
        field_grid.setColumnStretch(3, 1)

        self.in_codigo = QLineEdit()
        self.in_codigo.setPlaceholderText("Código (único)")
        self.in_codigo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre")
        self.in_nombre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.in_imed = QLineEdit()
        self.in_imed.setPlaceholderText("IMED (código)")
        self.in_imed.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Row 0: Código | in_codigo | Nombre | in_nombre
        field_grid.addWidget(QLabel("Código"), 0, 0)
        field_grid.addWidget(self.in_codigo, 0, 1)
        field_grid.addWidget(QLabel("Nombre"), 0, 2)
        field_grid.addWidget(self.in_nombre, 0, 3)

        # Row 1: IMED | in_imed
        field_grid.addWidget(QLabel("IMED"), 1, 0)
        field_grid.addWidget(self.in_imed, 1, 1)

        form_layout.addLayout(field_grid)

        # --- Actions row ---
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar en tabla…")
        self.in_filter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")

        self.btn_update = QPushButton("Actualizar seleccionado")
        self.btn_update.setProperty("variant", "ghost")
        self.btn_update.setEnabled(False)

        self.btn_toggle = QPushButton("Inactivar")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setEnabled(False)

        actions_row.addWidget(self.in_filter, 1)
        actions_row.addWidget(self.btn_create)
        actions_row.addWidget(self.btn_update)
        actions_row.addWidget(self.btn_toggle)

        form_layout.addLayout(actions_row)

        root.addWidget(form_card)

        # ===== Table card =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "IMED", "Estado"])
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

        # signals
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.on_create)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_toggle.clicked.connect(self.on_toggle_activo)
        self.table.itemSelectionChanged.connect(self._on_selected_row_changed)
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

        it = self.table.item(row, 0)  # Código (guardamos metadata acá)
        if not it:
            return None, None

        prestador_id = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        return (
            int(prestador_id) if prestador_id is not None else None,
            bool(activo) if activo is not None else None,
        )

    def _on_selected_row_changed(self) -> None:
        prestador_id, activo = self._selected()

        enabled = (prestador_id is not None)
        self.btn_update.setEnabled(enabled)
        self.btn_toggle.setEnabled(enabled)

        if enabled and activo is not None:
            self.btn_toggle.setText("Inactivar" if activo else "Restaurar")
        else:
            self.btn_toggle.setText("Inactivar")

        # autocompletar inputs desde fila
        row = self.table.currentRow()
        if row >= 0:
            it_cod = self.table.item(row, 0)
            it_nom = self.table.item(row, 1)
            it_imed = self.table.item(row, 2)

            self.in_codigo.setText(it_cod.text().strip() if it_cod else "")
            self.in_nombre.setText(it_nom.text().strip() if it_nom else "")
            self.in_imed.setText(it_imed.text().strip() if it_imed else "")

    # ---------------- data ----------------
    def load_data(self) -> None:
        try:
            rows = CatalogosWindowsUseCase.list_prestadores(solo_activos=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar prestadores:\n{e}")
            return

        self.table.setRowCount(0)

        for p in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_cod = QTableWidgetItem(p.codigo or "")
            it_cod.setData(Qt.ItemDataRole.UserRole, p.prestador_id)
            it_cod.setData(Qt.ItemDataRole.UserRole + 1, p.activo)
            it_cod.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, it_cod)

            it_nom = QTableWidgetItem(p.nombre or "(sin nombre)")
            it_nom.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 1, it_nom)

            it_imed = QTableWidgetItem(p.imed or "")
            it_imed.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, it_imed)

            it_estado = QTableWidgetItem("Activo" if p.activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_estado.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if p.activo else warn_bg()))
            self.table.setItem(r, 3, it_estado)

        self.btn_update.setEnabled(False)
        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText("Inactivar")

    # ---------------- actions ----------------
    def on_create(self) -> None:
        codigo = self.in_codigo.text().strip()
        nombre = self.in_nombre.text().strip()
        imed = self.in_imed.text().strip()

        try:
            CatalogosWindowsUseCase.create_prestador(
                codigo=codigo,
                nombre=nombre,
                imed=imed,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.in_codigo.clear()
        self.in_nombre.clear()
        self.in_imed.clear()
        self.load_data()

    def on_update(self) -> None:
        prestador_id, _activo = self._selected()
        if not prestador_id:
            QMessageBox.information(self, "Atención", "Seleccioná un prestador primero.")
            return

        codigo = self.in_codigo.text().strip()
        nombre = self.in_nombre.text().strip()
        imed = self.in_imed.text().strip()

        try:
            CatalogosWindowsUseCase.update_prestador(
                prestador_id=int(prestador_id),
                codigo=codigo,
                nombre=nombre,
                imed=imed,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_toggle_activo(self) -> None:
        prestador_id, activo = self._selected()
        if not prestador_id or activo is None:
            QMessageBox.information(self, "Atención", "Seleccioná un prestador primero.")
            return

        msg = "¿Marcar el prestador como INACTIVO?" if activo else "¿Restaurar (activar) el prestador seleccionado?"
        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            CatalogosWindowsUseCase.set_prestador_activo(
                prestador_id=int(prestador_id),
                activo=not bool(activo),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
