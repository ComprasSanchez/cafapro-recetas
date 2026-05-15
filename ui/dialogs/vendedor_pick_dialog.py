from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel
)

from ui.usecase.auditoria_visual_usecase import AuditoriaVisualUseCase, VendedorPickItemOut



class VendedorPickDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar vendedor")
        self.setModal(True)

        self._selected_id: int | None = None
        self._rows: list[VendedorPickItemOut] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Search
        top = QHBoxLayout()
        top.addWidget(QLabel("Buscar:"), 0)

        self.in_search = QLineEdit()
        self.in_search.setPlaceholderText("Código o descripción…")
        self.in_search.textChanged.connect(self._apply_filter)
        top.addWidget(self.in_search, 1)

        root.addLayout(top)

        # Table
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

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch(1)

        self.btn_ok = QPushButton("Seleccionar")
        self.btn_ok.setProperty("variant", "primary")
        self.btn_ok.setProperty("size", "md")
        self.btn_ok.clicked.connect(self._accept_from_current)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_cancel.setProperty("size", "md")
        self.btn_cancel.clicked.connect(self.reject)

        btns.addWidget(self.btn_cancel)
        btns.addWidget(self.btn_ok)

        root.addLayout(btns)

        self._load()

    def selected_vendedor_id(self) -> int | None:
        return self._selected_id

    def _load(self) -> None:
        self._rows = AuditoriaVisualUseCase.list_vendedores_activos()
        self._render(self._rows)

    def _apply_filter(self) -> None:
        q = (self.in_search.text() or "").strip().lower()
        if not q:
            self._render(self._rows)
            return

        filtered = [
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

            # guardo vendedor_id en la fila
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
        row = it.row()
        c0 = self.tbl.item(row, 0)
        if not c0:
            return

        self._selected_id = c0.data(Qt.ItemDataRole.UserRole)
        self.accept()
