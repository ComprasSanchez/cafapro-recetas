from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit, QComboBox, QSizePolicy
)

from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class PlanWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Planes")
        self.setMinimumSize(1050, 600)
        self.setWindowState(Qt.WindowState.WindowMaximized)

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

        title = QLabel("Planes")
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

        self.cb_obra = QComboBox()
        self.cb_obra.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.in_codigo = QLineEdit()
        self.in_codigo.setPlaceholderText("Código (opcional)")
        self.in_codigo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre (opcional)")
        self.in_nombre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Row 0: Obra social | cb_obra | Código | in_codigo
        field_grid.addWidget(QLabel("Obra social"), 0, 0)
        field_grid.addWidget(self.cb_obra, 0, 1)
        field_grid.addWidget(QLabel("Código"), 0, 2)
        field_grid.addWidget(self.in_codigo, 0, 3)

        # Row 1: Nombre | in_nombre
        field_grid.addWidget(QLabel("Nombre"), 1, 0)
        field_grid.addWidget(self.in_nombre, 1, 1)

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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Obra social", "Código", "Nombre", "Estado", "plan_id"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegate(BackgroundPriorityDelegate(self.table))

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setDefaultAlignment(Qt.AlignCenter)
        hh.setHighlightSections(False)

        # ocultamos plan_id pero lo dejamos por si querés debug
        self.table.setColumnHidden(4, True)

        tl.addWidget(self.table, 1)
        root.addWidget(table_card, 1)

        # signals
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.on_create)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_toggle.clicked.connect(self.on_toggle_activo)
        self.table.itemSelectionChanged.connect(self._on_selected_row_changed)
        self.in_filter.textChanged.connect(self._apply_filter)

        self._load_obras_sociales()
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

    # ---------------- data loaders ----------------
    def _load_obras_sociales(self) -> None:
        self.cb_obra.clear()
        try:
            obras = CatalogosWindowsUseCase.list_obras_sociales(solo_activas=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar obras sociales:\n{e}")
            return

        for os in obras:
            # texto visible
            label = f"{os.nombre} ({os.codigo})"
            self.cb_obra.addItem(label, os.obra_social_id)

    def load_data(self) -> None:
        try:
            plans = CatalogosWindowsUseCase.list_planes(solo_activos=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar planes:\n{e}")
            return

        self.table.setRowCount(0)

        for p in plans:
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_os = QTableWidgetItem(p.obra_social)
            it_os.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 0, it_os)

            it_cod = QTableWidgetItem(p.codigo or "")
            it_cod.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 1, it_cod)

            it_nom = QTableWidgetItem(p.nombre or "")
            it_nom.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 2, it_nom)

            it_estado = QTableWidgetItem("Activo" if p.activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_estado.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if p.activo else warn_bg()))
            self.table.setItem(r, 3, it_estado)

            it_id = QTableWidgetItem(str(p.plan_id))
            it_id.setTextAlignment(Qt.AlignCenter)
            # metadata en plan_id:
            it_id.setData(Qt.ItemDataRole.UserRole, p.plan_id)
            it_id.setData(Qt.ItemDataRole.UserRole + 1, p.activo)
            it_id.setData(Qt.ItemDataRole.UserRole + 2, p.obra_social_id)
            self.table.setItem(r, 4, it_id)

        self.btn_update.setEnabled(False)
        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText("Inactivar")

    # ---------------- selection helpers ----------------
    def _selected(self) -> tuple[int | None, bool | None, int | None]:
        row = self.table.currentRow()
        if row < 0:
            return None, None, None

        it = self.table.item(row, 4)  # plan_id item con metadata
        if not it:
            return None, None, None

        plan_id = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        obra_social_id = it.data(Qt.ItemDataRole.UserRole + 2)

        return (
            int(plan_id) if plan_id is not None else None,
            bool(activo) if activo is not None else None,
            int(obra_social_id) if obra_social_id is not None else None,
        )

    def _on_selected_row_changed(self) -> None:
        plan_id, activo, obra_social_id = self._selected()
        enabled = (plan_id is not None)

        self.btn_update.setEnabled(enabled)
        self.btn_toggle.setEnabled(enabled)

        if enabled and activo is not None:
            self.btn_toggle.setText("Inactivar" if activo else "Restaurar")
        else:
            self.btn_toggle.setText("Inactivar")

        # autocompletar inputs
        row = self.table.currentRow()
        if row >= 0:
            cod = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ""
            nom = self.table.item(row, 2).text().strip() if self.table.item(row, 2) else ""
            self.in_codigo.setText(cod)
            self.in_nombre.setText(nom)

            # seleccionar obra social del plan
            if obra_social_id is not None:
                idx = self.cb_obra.findData(obra_social_id)
                if idx >= 0:
                    self.cb_obra.setCurrentIndex(idx)

    # ---------------- actions ----------------
    def on_create(self) -> None:
        obra_social_id = self.cb_obra.currentData()
        codigo = self.in_codigo.text().strip() or None
        nombre = self.in_nombre.text().strip() or None

        if not obra_social_id:
            QMessageBox.warning(self, "Atención", "Seleccioná una obra social.")
            return

        try:
            CatalogosWindowsUseCase.create_plan(
                obra_social_id=int(obra_social_id),
                codigo=codigo,
                nombre=nombre,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.in_codigo.clear()
        self.in_nombre.clear()
        self.load_data()

    def on_update(self) -> None:
        plan_id, _activo, _osid = self._selected()
        if not plan_id:
            QMessageBox.information(self, "Atención", "Seleccioná un plan primero.")
            return

        obra_social_id = self.cb_obra.currentData()
        codigo = self.in_codigo.text().strip() or None
        nombre = self.in_nombre.text().strip() or None

        if not obra_social_id:
            QMessageBox.warning(self, "Atención", "Seleccioná una obra social.")
            return

        try:
            CatalogosWindowsUseCase.update_plan(
                plan_id=int(plan_id),
                obra_social_id=int(obra_social_id),
                codigo=codigo,
                nombre=nombre,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_toggle_activo(self) -> None:
        plan_id, activo, _osid = self._selected()
        if not plan_id or activo is None:
            QMessageBox.information(self, "Atención", "Seleccioná un plan primero.")
            return

        if activo:
            msg = "¿Marcar el plan como INACTIVO?"
        else:
            msg = "¿Restaurar (activar) el plan seleccionado?"

        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            CatalogosWindowsUseCase.set_plan_activo(
                plan_id=int(plan_id),
                activo=not bool(activo),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
