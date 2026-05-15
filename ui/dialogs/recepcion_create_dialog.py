from __future__ import annotations

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QPlainTextEdit, QDateTimeEdit, QLineEdit
)

from ui.usecase.recepcion_dialog_usecase import RecepcionDialogUseCase


class RecepcionCreateDialog(QDialog):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id
        self.created_recepcion_id: int | None = None

        self.setWindowTitle("Crear recepción")
        self.setMinimumWidth(600)
        self.setModal(True)

        self._build_ui()
        self._load_combos()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Nueva recepción")
        title.setProperty("role", "subtitle")
        root.addWidget(title)

        form = QFormLayout()

        self.cb_obra = QComboBox()
        self.cb_periodo = QComboBox()
        self.cb_prestador = QComboBox()
        self.cb_estado = QComboBox()

        self.dt_fecha = QDateTimeEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDateTime(QDateTime.currentDateTime())

        self.tx_obs = QPlainTextEdit()
        self.tx_obs.setPlaceholderText("Observaciones (opcional)")

        # Si querés mostrar “numero” pero lo genera DB: lo dejamos readonly
        self.in_numero = QLineEdit()
        self.in_numero.setPlaceholderText("Se asigna automáticamente")
        self.in_numero.setReadOnly(True)

        form.addRow("Obra social", self.cb_obra)
        form.addRow("Período", self.cb_periodo)
        form.addRow("Prestador", self.cb_prestador)
        form.addRow("Estado", self.cb_estado)
        form.addRow("Fecha Presentacion", self.dt_fecha)
        form.addRow("Observaciones", self.tx_obs)

        root.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_cancel.setProperty("size", "md")
        self.btn_ok = QPushButton("Crear")
        self.btn_ok.setProperty("variant", "primary")
        self.btn_ok.setProperty("size", "md")
        self.btn_ok.setDefault(True)

        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_ok)
        root.addLayout(actions)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_create)

    def _load_combos(self):
        try:
            obras, periodos, prestadores, estados = RecepcionDialogUseCase.load_create_catalogs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar datos:\n{e}")
            return

        self.cb_obra.clear()
        for o in obras:
            self.cb_obra.addItem(f"{o.nombre} ({o.codigo})", int(o.obra_social_id))

        self.cb_periodo.clear()
        for p in periodos:
            self.cb_periodo.addItem(f"{p.anio}-{p.mes:02d} Q{p.quincena}", int(p.periodo_id))

        self.cb_prestador.clear()
        for pr in prestadores:
            nombre = pr.nombre or ""
            self.cb_prestador.addItem(f"{pr.codigo} - {nombre}", int(pr.prestador_id))

        self.cb_estado.clear()
        for e in estados:
            self.cb_estado.addItem(str(e.descripcion), int(e.estado_recepcion_id))

        # opcional: preseleccionar ABIERTA si existe
        idx = self.cb_estado.findText("ABIERTA")
        if idx >= 0:
            self.cb_estado.setCurrentIndex(idx)

    def _on_create(self):
        obra_id = self.cb_obra.currentData()
        periodo_id = self.cb_periodo.currentData()
        prestador_id = self.cb_prestador.currentData()
        estado_recepcion_id = self.cb_estado.currentData()

        if obra_id is None or periodo_id is None or prestador_id is None or estado_recepcion_id is None:
            QMessageBox.information(self, "Atención", "Completá Obra Social / Período / Prestador / Estado.")
            return

        fecha = self.dt_fecha.dateTime().toPython()
        obs = self.tx_obs.toPlainText().strip() or None

        try:
            rec = RecepcionDialogUseCase.create_recepcion(
                obra_social_id=int(obra_id),
                periodo_id=int(periodo_id),
                prestador_id=int(prestador_id),
                estado_recepcion_id=int(estado_recepcion_id),
                fecha_presentacion=fecha,
                observaciones=obs,
                creado_por_usuario_id=self.creado_por_usuario_id,
            )

            self.created_recepcion_id = int(rec.recepcion_id)

            try:
                self.in_numero.setText(str(rec.numero))
            except Exception:
                pass

            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
