from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QFrame, QHeaderView
)

from ui.dialogs.recepcion_create_dialog import RecepcionCreateDialog
from ui.theme.delegates import BackgroundPriorityDelegate
from ui.usecase.recepciones_windows_usecase import RecepcionesWindowsUseCase


class RecepcionesWindow(QDialog):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self.setWindowTitle("Listado Recepciones")
        self.setMinimumSize(1100, 560)
        self.setWindowState(Qt.WindowState.WindowMaximized)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # -------------------------
        # Toolbar (card)
        # -------------------------
        toolbar = QFrame()
        toolbar.setObjectName("card")
        hl = QHBoxLayout(toolbar)
        hl.setContentsMargins(16, 12, 16, 12)
        hl.setSpacing(10)

        title = QLabel("Recepciones")
        title.setProperty("role", "title")

        self.in_filter = QLineEdit()
        self.in_filter.setPlaceholderText("Buscar…")

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_refresh.setProperty("variant", "ghost")
        self.btn_refresh.setProperty("size", "md")

        self.btn_create = QPushButton("Crear")
        self.btn_create.setProperty("variant", "primary")  # negro
        self.btn_create.setProperty("size", "md")

        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_delete.setProperty("variant", "danger")   # gris oscuro (no rojo)
        self.btn_delete.setProperty("size", "md")
        self.btn_delete.setEnabled(False)

        hl.addWidget(title)
        hl.addWidget(self.in_filter, 1)
        hl.addWidget(self.btn_refresh)
        hl.addWidget(self.btn_create)
        hl.addWidget(self.btn_delete)

        root.addWidget(toolbar, 0)

        # -------------------------
        # Table (card)
        # -------------------------
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(0)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Número Recepción", "Obra social", "Período", "Prestador", "Estado", "Fecha presentacion"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setItemDelegate(BackgroundPriorityDelegate(self.table))

        hh = self.table.horizontalHeader()
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hh.setStretchLastSection(True)

        # Ajuste: algunas columnas a contenido, otras estiran
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Número
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Fecha
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # Obra social
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Período
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # Prestador
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Estado

        tl.addWidget(self.table)
        root.addWidget(table_card, 1)

        # Signals
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_create.clicked.connect(self.open_create_dialog)
        self.btn_delete.clicked.connect(self.on_delete)
        self.table.itemSelectionChanged.connect(self._update_delete_state)
        self.in_filter.textChanged.connect(self._apply_filter)

        self.load_data()

    def _apply_filter(self, text: str) -> None:
        txt = text.strip().lower()
        for row in range(self.table.rowCount()):
            visible = not txt or any(
                txt in (self.table.item(row, c).text().lower() if self.table.item(row, c) else "")
                for c in range(self.table.columnCount())
            )
            self.table.setRowHidden(row, not visible)

    def _update_delete_state(self):
        self.btn_delete.setEnabled(self._selected_id() is not None)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        it = self.table.item(row, 0)  # Número
        if not it:
            return None
        rid = it.data(Qt.ItemDataRole.UserRole)
        return int(rid) if rid is not None else None

    def _fmt_dt(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y/%m/%d")
        return str(value).split(".")[0]

    def load_data(self):
        try:
            rows = RecepcionesWindowsUseCase.list_recepciones(include_closed=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar recepciones:\n{e}")
            return

        self.table.setRowCount(len(rows))

        for i, r in enumerate(rows):
            # Número + id oculto
            it_num = QTableWidgetItem(str(r.numero))
            it_num.setData(Qt.ItemDataRole.UserRole, r.recepcion_id)
            it_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, it_num)

            it_obs = QTableWidgetItem(str(getattr(r, "obra_social", "") or ""))
            it_obs.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 1, it_obs)

            it_per = QTableWidgetItem(str(getattr(r, "periodo", "") or ""))
            it_per.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 2, it_per)

            it_pre = QTableWidgetItem(str(getattr(r, "prestador", "") or ""))
            it_pre.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(i, 3, it_pre)

            it_est = QTableWidgetItem(str(getattr(r, "estado", "") or ""))
            it_est.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 4, it_est)

            it_fecha = QTableWidgetItem(self._fmt_dt(getattr(r, "fecha_presentacion", None)))
            it_fecha.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 5, it_fecha)

        self._update_delete_state()

    def open_create_dialog(self):
        dlg = RecepcionCreateDialog(self, creado_por_usuario_id=self.creado_por_usuario_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def on_delete(self):
        rid = self._selected_id()
        if not rid:
            QMessageBox.information(self, "Atención", "Seleccioná una recepción primero.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "¿Eliminar la recepción seleccionada? (eliminación física)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        try:
            RecepcionesWindowsUseCase.delete_recepcion(recepcion_id=rid)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
