from __future__ import annotations

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QPlainTextEdit, QDateTimeEdit, QLineEdit
)

from app.db.session import session_scope
from app.service.obra_social_service import ObraSocialService
from app.service.periodo_service import PeriodoService
from app.service.prestador_service import PrestadorService
from app.service.recepcion_service import RecepcionService


ESTADOS = ["ABIERTA"]  # ajustalo a tu negocio


class RecepcionCreateDialog(QDialog):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

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
        title.setStyleSheet("font-size:16px; font-weight:600;")
        root.addWidget(title)

        form = QFormLayout()

        self.cb_obra = QComboBox()
        self.cb_periodo = QComboBox()
        self.cb_prestador = QComboBox()

        self.cb_estado = QComboBox()
        for e in ESTADOS:
            self.cb_estado.addItem(e, e)

        self.dt_fecha = QDateTimeEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDateTime(QDateTime.currentDateTime())

        self.tx_obs = QPlainTextEdit()
        self.tx_obs.setPlaceholderText("Observaciones (opcional)")

        # Si querés mostrar “numero” pero lo genera DB: lo dejamos readonly y vacío
        self.in_numero = QLineEdit()
        self.in_numero.setPlaceholderText("Se asigna automáticamente")
        self.in_numero.setReadOnly(True)

        form.addRow("Obra social", self.cb_obra)
        form.addRow("Período", self.cb_periodo)
        form.addRow("Prestador", self.cb_prestador)
        form.addRow("Estado", self.cb_estado)
        form.addRow("Fecha recepción", self.dt_fecha)
        form.addRow("Observaciones", self.tx_obs)

        root.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_ok = QPushButton("Crear")
        self.btn_ok.setDefault(True)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_ok)
        root.addLayout(actions)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self._on_create)

    def _load_combos(self):
        try:
            with session_scope() as s:
                obras = ObraSocialService.list(s)
                periodos = PeriodoService.list(s)
                prestadores = PrestadorService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar datos:\n{e}")
            return

        self.cb_obra.clear()
        for o in obras:
            self.cb_obra.addItem(f"{o.nombre} ({o.codigo})", o.obra_social_id)

        self.cb_periodo.clear()
        for p in periodos:
            self.cb_periodo.addItem(f"{p.anio}-{p.mes:02d} Q{p.quincena}", p.periodo_id)

        self.cb_prestador.clear()
        for pr in prestadores:
            self.cb_prestador.addItem(f"{pr.codigo} - {pr.nombre}", pr.prestador_id)

    def _on_create(self):
        obra_id = self.cb_obra.currentData()
        periodo_id = self.cb_periodo.currentData()
        prestador_id = self.cb_prestador.currentData()
        estado = self.cb_estado.currentData()

        if obra_id is None or periodo_id is None or prestador_id is None:
            QMessageBox.information(self, "Atención", "Completá Obra Social / Período / Prestador.")
            return

        fecha = self.dt_fecha.dateTime().toPython()
        obs = self.tx_obs.toPlainText().strip() or None

        try:
            with session_scope() as s:
                rec = RecepcionService.create(
                    s,
                    obra_social_id=int(obra_id),
                    periodo_id=int(periodo_id),
                    prestador_id=int(prestador_id),
                    estado_recepcion=str(estado),
                    fecha_recepcion=fecha,
                    observaciones=obs,
                    creado_por_usuario_id=self.creado_por_usuario_id,
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        # Mostrar el número asignado por DB (opcional) y aceptar
        self.in_numero.setText(str(rec.numero))
        self.accept()
