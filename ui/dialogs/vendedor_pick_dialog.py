from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLabel, QFrame, QMessageBox,
)

from ui.usecase.auditoria_visual_usecase import AuditoriaVisualUseCase, VendedorPickItemOut
from ui.usecase.catalogos_windows_usecase import CatalogosWindowsUseCase


class VendedorPickDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar vendedor")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._selected_id: int | None = None
        self._rows: list[VendedorPickItemOut] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        # ── Búsqueda ──────────────────────────────────────────
        top = QHBoxLayout()
        top.addWidget(QLabel("Buscar:"), 0)
        self.in_search = QLineEdit()
        self.in_search.setPlaceholderText("Código o descripción…")
        self.in_search.textChanged.connect(self._apply_filter)
        top.addWidget(self.in_search, 1)
        root.addLayout(top)

        # ── Tabla ─────────────────────────────────────────────
        self.tbl = QTableWidget()
        self.tbl.setColumnCount(2)
        self.tbl.setHorizontalHeaderLabels(["Código", "Descripción"])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.itemDoubleClicked.connect(self._accept_from_current)
        root.addWidget(self.tbl, 1)

        # ── Panel "Nuevo vendedor" (oculto por defecto) ───────
        self._create_panel = QFrame()
        self._create_panel.setObjectName("card")
        cp_lay = QVBoxLayout(self._create_panel)
        cp_lay.setContentsMargins(12, 10, 12, 10)
        cp_lay.setSpacing(8)

        cp_title = QLabel("Nuevo vendedor")
        cp_title.setObjectName("sectionTitle")
        cp_lay.addWidget(cp_title)

        fields_row = QHBoxLayout()
        fields_row.setSpacing(8)

        fields_row.addWidget(QLabel("Código:"))
        self.in_nuevo_codigo = QLineEdit()
        self.in_nuevo_codigo.setPlaceholderText("Código único")
        fields_row.addWidget(self.in_nuevo_codigo, 1)

        fields_row.addWidget(QLabel("Descripción:"))
        self.in_nuevo_desc = QLineEdit()
        self.in_nuevo_desc.setPlaceholderText("Nombre del vendedor")
        fields_row.addWidget(self.in_nuevo_desc, 2)

        self.btn_confirmar_crear = QPushButton("Crear")
        self.btn_confirmar_crear.setProperty("variant", "primary")
        fields_row.addWidget(self.btn_confirmar_crear)

        self.btn_cancelar_crear = QPushButton("Cancelar")
        self.btn_cancelar_crear.setProperty("variant", "ghost")
        fields_row.addWidget(self.btn_cancelar_crear)

        cp_lay.addLayout(fields_row)

        self.lb_create_error = QLabel("")
        self.lb_create_error.setProperty("role", "error")
        self.lb_create_error.setVisible(False)
        cp_lay.addWidget(self.lb_create_error)

        self._create_panel.setVisible(False)
        root.addWidget(self._create_panel)

        # ── Botones principales ───────────────────────────────
        btns = QHBoxLayout()
        btns.setSpacing(8)

        self.btn_nuevo = QPushButton("+ Nuevo vendedor")
        self.btn_nuevo.setProperty("variant", "ghost")
        btns.addWidget(self.btn_nuevo)

        btns.addStretch(1)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_ok = QPushButton("Seleccionar")
        self.btn_ok.setProperty("variant", "primary")

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)
        root.addLayout(btns)

        # señales
        self.btn_ok.clicked.connect(self._accept_from_current)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_nuevo.clicked.connect(self._show_create_panel)
        self.btn_confirmar_crear.clicked.connect(self._on_crear_vendedor)
        self.btn_cancelar_crear.clicked.connect(self._hide_create_panel)
        self.in_nuevo_desc.returnPressed.connect(self._on_crear_vendedor)

        self._load()

    # ── Selección ─────────────────────────────────────────────

    def selected_vendedor_id(self) -> int | None:
        return self._selected_id

    def _load(self) -> None:
        self._rows = AuditoriaVisualUseCase.list_vendedores_activos()
        self._render(self._rows)

    def _apply_filter(self) -> None:
        q = (self.in_search.text() or "").strip().lower()
        filtered = self._rows if not q else [
            r for r in self._rows
            if q in (getattr(r, "codigo", "") or "").lower()
            or q in (getattr(r, "descripcion", "") or "").lower()
        ]
        self._render(filtered)

    def _render(self, rows: list[VendedorPickItemOut]) -> None:
        self.tbl.setRowCount(len(rows))
        for i, r in enumerate(rows):
            it0 = QTableWidgetItem(str(getattr(r, "codigo", "") or ""))
            it1 = QTableWidgetItem(str(getattr(r, "descripcion", "") or ""))
            it0.setData(Qt.ItemDataRole.UserRole, int(getattr(r, "vendedor_id")))
            self.tbl.setItem(i, 0, it0)
            self.tbl.setItem(i, 1, it1)
        if rows:
            self.tbl.setCurrentCell(0, 0)
            self.tbl.selectRow(0)

    def _accept_from_current(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            return
        c0 = self.tbl.item(it.row(), 0)
        if not c0:
            return
        self._selected_id = c0.data(Qt.ItemDataRole.UserRole)
        self.accept()

    # ── Crear vendedor ────────────────────────────────────────

    def _show_create_panel(self) -> None:
        self._create_panel.setVisible(True)
        self.btn_nuevo.setVisible(False)
        self.lb_create_error.setVisible(False)
        self.in_nuevo_codigo.clear()
        self.in_nuevo_desc.clear()
        self.in_nuevo_codigo.setFocus()
        self.adjustSize()

    def _hide_create_panel(self) -> None:
        self._create_panel.setVisible(False)
        self.btn_nuevo.setVisible(True)

    def _on_crear_vendedor(self) -> None:
        codigo = self.in_nuevo_codigo.text().strip()
        descripcion = self.in_nuevo_desc.text().strip()

        if not codigo or not descripcion:
            self.lb_create_error.setText("Completá código y descripción.")
            self.lb_create_error.setVisible(True)
            return

        try:
            CatalogosWindowsUseCase.create_vendedor(
                codigo=codigo,
                descripcion=descripcion,
            )
        except Exception as e:
            self.lb_create_error.setText(str(e))
            self.lb_create_error.setVisible(True)
            return

        # recargar, seleccionar y aceptar directamente
        self._load()
        self._select_by_codigo(codigo)
        self._accept_from_current()

    def _select_by_codigo(self, codigo: str) -> None:
        for row in range(self.tbl.rowCount()):
            it = self.tbl.item(row, 0)
            if it and it.text().strip().lower() == codigo.lower():
                self.tbl.setCurrentCell(row, 0)
                self.tbl.selectRow(row)
                return
