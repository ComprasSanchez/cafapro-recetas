from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QLabel
)

from app.db.session import session_scope
from app.service.estado_seguimiento_service import EstadoSeguimientoService


class EstadoSeguimientoPickDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar estado de seguimiento")
        self.setModal(True)

        self._selected_id: int | None = None
        self._rows = []

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addWidget(QLabel("Seleccioná el estado de seguimiento:"), 0)

        self.tbl = QTableWidget()
        self.tbl.setColumnCount(1)
        self.tbl.setHorizontalHeaderLabels(["Descripción"])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl.itemDoubleClicked.connect(self._accept_from_current)

        root.addWidget(self.tbl, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("Seleccionar")
        btn_ok.clicked.connect(self._accept_from_current)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_ok)
        root.addLayout(btns)

        self._load()

    def selected_estado_seguimiento_id(self) -> int | None:
        return self._selected_id

    def _load(self) -> None:
        with session_scope() as s:
            self._rows = EstadoSeguimientoService.list(s)

        self.tbl.setRowCount(len(self._rows))
        for i, r in enumerate(self._rows):
            it = QTableWidgetItem(str(getattr(r, "descripcion", "") or ""))
            it.setData(Qt.ItemDataRole.UserRole, int(getattr(r, "estado_seguimiento_id")))
            self.tbl.setItem(i, 0, it)

        if self._rows:
            self.tbl.setCurrentCell(0, 0)
            self.tbl.selectRow(0)

    def _accept_from_current(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            return
        self._selected_id = it.data(Qt.ItemDataRole.UserRole)
        self.accept()
