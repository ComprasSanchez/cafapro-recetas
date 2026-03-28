from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit
)

from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class VendedoresWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Vendedores")
        self.setMinimumSize(950, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Header =====
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Vendedores")
        title.setProperty("role", "title")
        hl.addWidget(title)
        hl.addStretch(1)

        root.addWidget(header)

        # ===== CRUD panel =====
        card = QFrame()
        card.setObjectName("card")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(10)

        self.in_codigo = QLineEdit()
        self.in_codigo.setPlaceholderText("Código (único)")
        self.in_codigo.setMinimumHeight(28)
        self.in_codigo.setFixedWidth(180)

        self.in_descripcion = QLineEdit()
        self.in_descripcion.setPlaceholderText("Descripción")
        self.in_descripcion.setMinimumHeight(28)
        self.in_descripcion.setMinimumWidth(220)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        self.btn_refresh.setMinimumHeight(32)

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")
        self.btn_create.setMinimumHeight(32)

        self.btn_update = QPushButton("Actualizar seleccionado")
        self.btn_update.setProperty("variant", "ghost")
        self.btn_update.setMinimumHeight(32)
        self.btn_update.setEnabled(False)

        self.btn_toggle = QPushButton("Inactivar")
        self.btn_toggle.setProperty("variant", "ghost")
        self.btn_toggle.setMinimumHeight(32)
        self.btn_toggle.setEnabled(False)

        cl.addWidget(QLabel("Código"))
        cl.addWidget(self.in_codigo)
        cl.addWidget(QLabel("Descripción"))
        cl.addWidget(self.in_descripcion)
        cl.addStretch(1)
        cl.addWidget(self.btn_refresh)
        cl.addWidget(self.btn_create)
        cl.addWidget(self.btn_update)
        cl.addWidget(self.btn_toggle)

        root.addWidget(card)

        # ===== Table =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Código", "Descripción", "Estado"])
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

        # signals
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.on_create)
        self.btn_update.clicked.connect(self.on_update)
        self.btn_toggle.clicked.connect(self.on_toggle_activo)
        self.table.itemSelectionChanged.connect(self._on_selected_row_changed)

        self.load_data()

    # ---------------- selection helpers ----------------
    def _selected(self) -> tuple[int | None, bool | None]:
        row = self.table.currentRow()
        if row < 0:
            return None, None

        it = self.table.item(row, 0)  # Código (guardamos metadata acá)
        if not it:
            return None, None

        vendedor_id = it.data(Qt.ItemDataRole.UserRole)
        activo = it.data(Qt.ItemDataRole.UserRole + 1)
        return (
            int(vendedor_id) if vendedor_id is not None else None,
            bool(activo) if activo is not None else None,
        )

    def _on_selected_row_changed(self) -> None:
        vendedor_id, activo = self._selected()

        enabled = (vendedor_id is not None)
        self.btn_update.setEnabled(enabled)
        self.btn_toggle.setEnabled(enabled)

        if enabled and activo is not None:
            self.btn_toggle.setText("Inactivar" if activo else "Restaurar")
        else:
            self.btn_toggle.setText("Inactivar")

        # autocompletar inputs
        row = self.table.currentRow()
        if row >= 0:
            it_cod = self.table.item(row, 0)
            it_desc = self.table.item(row, 1)
            if it_cod and it_desc:
                self.in_codigo.setText(it_cod.text().strip())
                self.in_descripcion.setText(it_desc.text().strip())

    # ---------------- data ----------------
    def load_data(self) -> None:
        try:
            rows = CatalogosWindowsUseCase.list_vendedores(solo_activos=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar vendedores:\n{e}")
            return

        self.table.setRowCount(0)

        for v in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_cod = QTableWidgetItem(v.codigo or "")
            it_cod.setData(Qt.ItemDataRole.UserRole, v.vendedor_id)
            it_cod.setData(Qt.ItemDataRole.UserRole + 1, v.activo)
            it_cod.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 0, it_cod)

            it_desc = QTableWidgetItem(v.descripcion or "")
            it_desc.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(r, 1, it_desc)

            it_estado = QTableWidgetItem("Activo" if v.activo else "Inactivo")
            it_estado.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(r, 2, it_estado)

        # reset estado botones
        self.btn_update.setEnabled(False)
        self.btn_toggle.setEnabled(False)
        self.btn_toggle.setText("Inactivar")

    # ---------------- actions ----------------
    def on_create(self) -> None:
        codigo = self.in_codigo.text().strip()
        descripcion = self.in_descripcion.text().strip()

        try:
            CatalogosWindowsUseCase.create_vendedor(
                codigo=codigo,
                descripcion=descripcion,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.in_codigo.clear()
        self.in_descripcion.clear()
        self.load_data()

    def on_update(self) -> None:
        vendedor_id, _activo = self._selected()
        if not vendedor_id:
            QMessageBox.information(self, "Atención", "Seleccioná un vendedor primero.")
            return

        codigo = self.in_codigo.text().strip()
        descripcion = self.in_descripcion.text().strip()

        try:
            CatalogosWindowsUseCase.update_vendedor(
                vendedor_id=int(vendedor_id),
                codigo=codigo,
                descripcion=descripcion,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()

    def on_toggle_activo(self) -> None:
        vendedor_id, activo = self._selected()
        if not vendedor_id or activo is None:
            QMessageBox.information(self, "Atención", "Seleccioná un vendedor primero.")
            return

        msg = "¿Marcar el vendedor como INACTIVO?" if activo else "¿Restaurar (activar) el vendedor seleccionado?"
        resp = QMessageBox.question(
            self,
            "Confirmar",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            CatalogosWindowsUseCase.set_vendedor_activo(
                vendedor_id=int(vendedor_id),
                activo=not bool(activo),
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
