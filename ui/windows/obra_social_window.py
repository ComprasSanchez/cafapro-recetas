from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator, QBrush
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit, QComboBox, QSpacerItem, QSizePolicy
)

from ui.theme.delegates import BackgroundPriorityDelegate
from ui.theme.row_colors import ok_bg, warn_bg
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class ObrasSocialesWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Obras Sociales")
        self.setMinimumSize(1180, 560)
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
        title = QLabel("Obras Sociales")
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

        self.in_codigo = QLineEdit()
        self.in_codigo.setPlaceholderText("Código (único)")

        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre")

        self.cb_validador = QComboBox()
        self.cb_validador.addItems(["imed", "preserfar", "facaf"])

        self.in_dias_venc = QLineEdit()
        self.in_dias_venc.setPlaceholderText("Días venc.")
        self.in_dias_venc.setValidator(QIntValidator(0, 3650, self))

        self.in_codigo_fin = QLineEdit()
        self.in_codigo_fin.setPlaceholderText("Cod. financiador")
        self.in_codigo_fin.setValidator(QIntValidator(0, 2_000_000_000, self))

        # Row 0: Código | in_codigo | Nombre | in_nombre
        field_grid.addWidget(QLabel("Código"), 0, 0)
        field_grid.addWidget(self.in_codigo, 0, 1)
        field_grid.addWidget(QLabel("Nombre"), 0, 2)
        field_grid.addWidget(self.in_nombre, 0, 3)

        # Row 1: Validador | cb_validador | Días venc. | in_dias_venc
        field_grid.addWidget(QLabel("Validador"), 1, 0)
        field_grid.addWidget(self.cb_validador, 1, 1)
        field_grid.addWidget(QLabel("Días venc."), 1, 2)
        field_grid.addWidget(self.in_dias_venc, 1, 3)

        # Row 2: Cod. financiador | in_codigo_fin
        field_grid.addWidget(QLabel("Cod. financiador"), 2, 0)
        field_grid.addWidget(self.in_codigo_fin, 2, 1)

        form_l.addLayout(field_grid)

        # actions row
        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar en tabla…")

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
        form_l.addLayout(actions_row)

        root.addWidget(form_card)

        # ===== table_card =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Código",
            "Nombre",
            "Validador",
            "Dias venc.",
            "Cod. financiador",
            "Estado",
        ])
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

        obra_social_id = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        return (int(obra_social_id) if obra_social_id is not None else None,
                bool(activo) if activo is not None else None)

    def _on_selected_row_changed(self) -> None:
        rid, activo = self._selected()

        enabled = (rid is not None)
        self.btn_update.setEnabled(enabled)
        self.btn_toggle.setEnabled(enabled)

        if enabled and activo is not None:
            self.btn_toggle.setText("Inactivar" if activo else "Restaurar")
        else:
            self.btn_toggle.setText("Inactivar")

        # autocompletar inputs con fila seleccionada
        row = self.table.currentRow()
        if row >= 0:
            it_cod = self.table.item(row, 0)
            it_nom = self.table.item(row, 1)
            it_val = self.table.item(row, 2)
            it_dias = self.table.item(row, 3)
            it_fin = self.table.item(row, 4)
            if it_cod and it_nom:
                self.in_codigo.setText(it_cod.text().strip())
                self.in_nombre.setText(it_nom.text().strip())
                self.cb_validador.setCurrentText((it_val.text().strip() if it_val else "imed") or "imed")
                self.in_dias_venc.setText("" if (not it_dias or it_dias.text().strip() == "-") else it_dias.text().strip())
                self.in_codigo_fin.setText("" if (not it_fin or it_fin.text().strip() == "-") else it_fin.text().strip())

    # ---------------- data ----------------
    def load_data(self) -> None:
        try:
            rows = CatalogosWindowsUseCase.list_obras_sociales(solo_activas=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar obras sociales:\n{e}")
            return

        self.table.setRowCount(0)

        for os in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_cod = QTableWidgetItem(os.codigo)
            it_cod.setData(Qt.ItemDataRole.UserRole, os.obra_social_id)
            it_cod.setData(Qt.ItemDataRole.UserRole + 1, os.activo)
            it_cod.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, it_cod)

            it_nom = QTableWidgetItem(os.nombre)
            it_nom.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 1, it_nom)

            it_val = QTableWidgetItem(os.validador or "imed")
            it_val.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 2, it_val)

            it_dias = QTableWidgetItem(str(os.dias_vencimiento) if os.dias_vencimiento is not None else "-")
            it_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 3, it_dias)

            it_fin = QTableWidgetItem(str(os.codigo_financiador) if os.codigo_financiador is not None else "-")
            it_fin.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 4, it_fin)

            it_estado = QTableWidgetItem("Activo" if os.activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            it_estado.setData(Qt.ItemDataRole.BackgroundRole, QBrush(ok_bg() if os.activo else warn_bg()))
            self.table.setItem(r, 5, it_estado)

        # reset estado botones
        self.btn_update.setEnabled(False)
        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText("Inactivar")

    # ---------------- actions ----------------
    def on_create(self) -> None:
        codigo = self.in_codigo.text().strip()
        nombre = self.in_nombre.text().strip()
        validador = self.cb_validador.currentText().strip().lower()
        dias_venc = self.in_dias_venc.text().strip()
        codigo_fin = self.in_codigo_fin.text().strip()

        try:
            CatalogosWindowsUseCase.create_obra_social(
                codigo=codigo,
                nombre=nombre,
                validador=validador,
                dias_vencimiento=dias_venc or None,
                codigo_financiador=codigo_fin or None,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.in_codigo.clear()
        self.in_nombre.clear()
        self.in_dias_venc.clear()
        self.in_codigo_fin.clear()
        self.cb_validador.setCurrentText("imed")
        self.load_data()

    def on_update(self) -> None:
        obra_social_id, _activo = self._selected()
        if not obra_social_id:
            QMessageBox.information(self, "Atención", "Seleccioná una obra social primero.")
            return

        codigo = self.in_codigo.text().strip()
        nombre = self.in_nombre.text().strip()
        validador = self.cb_validador.currentText().strip().lower()
        dias_venc = self.in_dias_venc.text().strip()
        codigo_fin = self.in_codigo_fin.text().strip()

        try:
            CatalogosWindowsUseCase.update_obra_social(
                obra_social_id=obra_social_id,
                codigo=codigo,
                nombre=nombre,
                validador=validador,
                dias_vencimiento=dias_venc or None,
                codigo_financiador=codigo_fin or None,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_toggle_activo(self) -> None:
        obra_social_id, activo = self._selected()
        if not obra_social_id or activo is None:
            QMessageBox.information(self, "Atención", "Seleccioná una obra social primero.")
            return

        if activo:
            msg = "¿Marcar la obra social como INACTIVA?"
        else:
            msg = "¿Restaurar (activar) la obra social seleccionada?"

        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            CatalogosWindowsUseCase.set_obra_social_activa(
                obra_social_id=obra_social_id,
                activo=not bool(activo),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
