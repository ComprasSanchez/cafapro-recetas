from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox,
    QHeaderView, QLineEdit, QComboBox
)

from app.db.session import session_scope
from app.service.catalogos.obra_social_service import ObraSocialService
from app.service.catalogos.plan_service import PlanService


class PlanWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Planes")
        self.setMinimumSize(1050, 600)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ===== Header =====
        header = QFrame()
        header.setObjectName("card")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 10)
        hl.setSpacing(10)

        title = QLabel("Planes")
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

        self.cb_obra = QComboBox()
        self.cb_obra.setMinimumHeight(28)
        self.cb_obra.setMinimumWidth(200)

        self.in_codigo = QLineEdit()
        self.in_codigo.setPlaceholderText("Código (opcional)")
        self.in_codigo.setMinimumHeight(28)
        self.in_codigo.setFixedWidth(180)

        self.in_nombre = QLineEdit()
        self.in_nombre.setPlaceholderText("Nombre (opcional)")
        self.in_nombre.setMinimumHeight(28)
        self.in_nombre.setMinimumWidth(200)

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

        cl.addWidget(QLabel("Obra social"))
        cl.addWidget(self.cb_obra)
        cl.addWidget(QLabel("Código"))
        cl.addWidget(self.in_codigo)
        cl.addWidget(QLabel("Nombre"))
        cl.addWidget(self.in_nombre)

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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Obra social", "Código", "Nombre", "Estado", "plan_id"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

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

        self._load_obras_sociales()
        self.load_data()

    # ---------------- data loaders ----------------
    def _load_obras_sociales(self) -> None:
        self.cb_obra.clear()
        try:
            with session_scope() as s:
                obras = ObraSocialService.list(s, solo_activas=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar obras sociales:\n{e}")
            return

        for os in obras:
            # texto visible
            label = f"{os.nombre} ({os.codigo})"
            self.cb_obra.addItem(label, os.obra_social_id)

    def load_data(self) -> None:
        try:
            with session_scope() as s:
                plans = PlanService.list(s, solo_activos=False)
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
            it_estado.setTextAlignment(Qt.AlignCenter)
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
            with session_scope() as s:
                PlanService.create(
                    s,
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
            with session_scope() as s:
                PlanService.update(
                    s,
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
            with session_scope() as s:
                if activo:
                    PlanService.delete_logico(s, int(plan_id))
                else:
                    PlanService.restore(s, int(plan_id))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_data()
