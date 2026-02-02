from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit
)

from app.db.session import session_scope
from app.service.catalogos.prestador_service import PrestadorService


class PrestadoresWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prestadores")
        self.setMinimumSize(1050, 580)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Header =====
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Prestadores")
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

        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre")
        self.in_nombre.setMinimumHeight(28)
        self.in_nombre.setMinimumWidth(320)

        self.in_imed = QLineEdit()
        self.in_imed.setPlaceholderText("IMED (código)")
        self.in_imed.setMinimumHeight(28)
        self.in_imed.setFixedWidth(180)

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
        cl.addWidget(QLabel("Nombre"))
        cl.addWidget(self.in_nombre)
        cl.addWidget(QLabel("IMED"))
        cl.addWidget(self.in_imed)

        cl.addStretch(1)
        cl.addWidget(self.btn_refresh)
        cl.addWidget(self.btn_create)
        cl.addWidget(self.btn_update)
        cl.addWidget(self.btn_toggle)

        root.addWidget(card)

        # ===== Tabla =====
        table_card = QFrame()
        table_card.setObjectName("card")
        tl = QVBoxLayout(table_card)
        tl.setContentsMargins(12, 12, 12, 12)
        tl.setSpacing(8)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Código", "Nombre", "IMED", "Estado"])
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
            with session_scope() as s:
                rows = PrestadorService.list(s, solo_activos=False)  # ✅ trae todo
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
            it_estado.setTextAlignment(Qt.AlignCenter)
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
            with session_scope() as s:
                PrestadorService.create(s, codigo=codigo, nombre=nombre, imed=imed)
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
            with session_scope() as s:
                PrestadorService.update(
                    s,
                    prestador_id=int(prestador_id),
                    codigo=codigo,
                    nombre=nombre,
                    imed=imed,  # ✅ acá se actualiza el IMED
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
            with session_scope() as s:
                if activo:
                    PrestadorService.delete_logico(s, int(prestador_id))
                else:
                    PrestadorService.restore(s, int(prestador_id))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
