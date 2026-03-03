from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame,
    QLineEdit, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QMenu
)

from app.db.session import session_scope
from app.service.debitos.motivos_debito_service import MotivosDebitosService


class MotivosDebitosWindow(QDialog):
    ROW_H = 36

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motivos de Débito")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        self._build_ui()
        self._load_data()

    # ---------------- UI ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # -------- Formulario --------
        form_card = QFrame()
        form_card.setObjectName("card")
        form_l = QHBoxLayout(form_card)
        form_l.setContentsMargins(12, 10, 12, 10)
        form_l.setSpacing(8)

        self.in_descripcion = QLineEdit()
        self.in_descripcion.setPlaceholderText("Descripción")
        form_l.addWidget(self.in_descripcion, 1)

        self.cb_lado = QComboBox()
        self.cb_lado.addItem("Frente", "F")
        self.cb_lado.addItem("Dorso", "D")
        form_l.addWidget(self.cb_lado, 0)

        self.btn_add = QPushButton("Agregar")
        self.btn_add.setProperty("variant", "primary")
        self.btn_add.clicked.connect(self._create)
        form_l.addWidget(self.btn_add, 0)

        root.addWidget(form_card, 0)

        # -------- Tabla --------
        table_card = QFrame()
        table_card.setObjectName("card")
        table_l = QVBoxLayout(table_card)
        table_l.setContentsMargins(12, 12, 12, 12)

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
        self.tbl.customContextMenuRequested.connect(self._on_context_menu)

        table_l.addWidget(self.tbl)
        root.addWidget(table_card, 1)

    # ---------------- CREATE ----------------
    def _create(self):
        desc = (self.in_descripcion.text() or "").strip()
        lado = self.cb_lado.currentData()

        if not desc:
            QMessageBox.warning(self, "Falta dato", "La descripción es obligatoria.")
            return

        try:
            with session_scope() as s:
                with session_scope() as s:
                    MotivosDebitosService.create(
                        s,
                        descripcion=desc,
                        lado=lado,
                    )

            self.in_descripcion.clear()
            self._load_data()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # ---------------- LOAD ----------------
    def _load_data(self):
        with session_scope() as s:
            rows = MotivosDebitosService.list(s)

        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            self.tbl.setRowHeight(i, self.ROW_H)

            self._set_item(i, 0, r.descripcion)
            self._set_item(i, 1, r.lado.value)
            self._set_item(i, 2, "Sí" if r.activo else "No")

            btn = QPushButton("Dar de baja" if r.activo else "Activar")
            btn.clicked.connect(lambda _, rid=r.motivo_debito_id: self._toggle(rid))
            self.tbl.setCellWidget(i, 3, btn)

            it = QTableWidgetItem(r.descripcion)
            it.setData(Qt.UserRole, r.motivo_debito_id)
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.tbl.setItem(i, 0, it)

    # ---------------- TOGGLE BAJA LÓGICA ----------------
    def _toggle(self, motivo_id: int):
        try:
            with session_scope() as s:
                MotivosDebitosService.toggle_activo(s, motivo_id)
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