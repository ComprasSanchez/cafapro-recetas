from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QHBoxLayout, QLabel, QPushButton,
    QDateEdit, QMessageBox, QLineEdit, QSizePolicy, QGridLayout
)

from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.recepcion_create_dialog import RecepcionCreateDialog


class LotesTemporalesTab(QWidget):
    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._fecha: datetime | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = self._build_header()
        root.addWidget(header)

        # root.addWidget(...)

    def _ro_line(text: str = "-") -> QLineEdit:
        """LineEdit readonly con look de display."""
        le = QLineEdit(text)
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.NoFocus)
        le.setMinimumHeight(26)
        le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return le

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(90)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # ===== Controles =====
        lb_num = QLabel("N° Recepción:")
        self.in_numero = self._ro_line()
        self.in_numero.setFixedWidth(90)

        self.btn_pick_recepcion = QPushButton("…")
        self.btn_pick_recepcion.setFixedSize(32, 26)

        self.btn_new_recepcion = QPushButton("+")
        self.btn_new_recepcion.setFixedSize(32, 26)

        lb_obra = QLabel("Obra social:")
        self.in_obra = self._ro_line()
        self.in_obra.setFixedWidth(360)

        lb_prest = QLabel("Prestador:")
        self.in_prestador = self._ro_line()
        self.in_prestador.setFixedWidth(360)

        lb_periodo = QLabel("Período:")
        self.in_periodo = self._ro_line()
        self.in_periodo.setFixedWidth(120)

        lb_quincena = QLabel("Quincena:")
        self.in_quincena = self._ro_line()
        self.in_quincena.setFixedWidth(70)
        self.in_quincena.setAlignment(Qt.AlignCenter)

        self.btn_set_fecha = QPushButton("Fecha")
        self.btn_set_fecha.setFixedHeight(26)

        self.de_fecha = QDateEdit()
        self.de_fecha.setCalendarPopup(True)
        self.de_fecha.setDate(QDate.currentDate())
        self.de_fecha.setDisplayFormat("dd/MM/yyyy")
        self.de_fecha.setFixedSize(110, 26)

        # ===== Bloque compacto para N° Recepción + botones =====
        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(4)

        # El input ocupa todo el espacio disponible
        self.in_numero.setMinimumWidth(140)
        self.in_numero.setMaximumWidth(9999)  # por si venía limitado antes
        self.in_numero.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Los botones quedan pegados al input
        self.btn_pick_recepcion.setFixedSize(32, 26)
        self.btn_new_recepcion.setFixedSize(32, 26)

        num_l.addWidget(self.in_numero, 1)  # stretch=1
        num_l.addWidget(self.btn_pick_recepcion, 0)
        num_l.addWidget(self.btn_new_recepcion, 0)

        # ===== Layout (2 filas) =====
        # Fila 0
        grid.addWidget(lb_num, 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(num_box, 0, 1, 1, 3)  # ocupa columnas 1..3 (compacto)

        grid.addWidget(lb_obra, 0, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_obra, 0, 5, 1, 4)

        # Fila 1
        grid.addWidget(lb_prest, 1, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_prestador, 1, 1, 1, 3)

        grid.addWidget(lb_periodo, 1, 4, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_periodo, 1, 5)

        grid.addWidget(lb_quincena, 1, 6, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(self.in_quincena, 1, 7)

        grid.addWidget(self.btn_set_fecha, 1, 8)
        grid.addWidget(self.de_fecha, 1, 9)

        # Columna elástica
        grid.setColumnStretch(10, 1)

        # ===== Signals =====
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)
        self.btn_new_recepcion.clicked.connect(self._on_new_recepcion)
        self.btn_set_fecha.clicked.connect(self._on_set_fecha)

        return header

    # --------------------------
    # Recepción: cargar / mostrar
    # --------------------------
    def _on_pick_recepcion(self):
        dlg = RecepcionPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        rid = dlg.selected_recepcion_id()
        if not rid:
            return

        self._load_recepcion(rid)

    def _on_new_recepcion(self):
        dlg = RecepcionCreateDialog(self, creado_por_usuario_id=self.creado_por_usuario_id)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.created_recepcion_id:
            self._load_recepcion(dlg.created_recepcion_id)

        # Si tu RecepcionCreateDialog no devuelve recepcion_id,
        # recargamos lista y dejamos que el usuario la elija.
        # Mejor: hacer que el dialog guarde el id creado (ver nota abajo).
        # Por ahora: pedimos que se seleccione (simple).
        QMessageBox.information(self, "OK", "Recepción creada. Ahora seleccionála con 'Elegir recepción…'.")

    def _load_recepcion(self, recepcion_id: int):
        # Si querés una consulta puntual por id, lo ideal es agregar:
        # RecepcionService.get(s, recepcion_id)
        # Por ahora, reutilizo list() y filtro.
        try:
            with session_scope() as s:
                rows = RecepcionService.list(s)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la recepción:\n{e}")
            return

        rec = next((x for x in rows if x.recepcion_id == recepcion_id), None)
        if not rec:
            QMessageBox.warning(self, "Atención", "No se encontró la recepción seleccionada.")
            return

        self._recepcion_id = rec.recepcion_id

        # Datos directos
        self.in_numero.setText(f"{rec.numero}")
        self.in_prestador.setText(f"{rec.prestador}")
        self.in_obra.setText(f"{rec.obra_social}")

        # Periodo / Quincena
        # Si rec.periodo ya viene como "2026-01 Q1", lo partimos:
        periodo_txt = str(rec.periodo)
        self.in_periodo.setText(f"{periodo_txt}")

        # Intento sacar quincena de "Q1" o "Q2"
        quincena = "-"
        if "Q1" in periodo_txt:
            quincena = "1ª"
        elif "Q2" in periodo_txt:
            quincena = "2ª"
        self.in_quincena.setText(f"{quincena}")

    # --------------------------
    # Fecha
    # --------------------------
    def _on_set_fecha(self):
        # Por ahora solo lo guarda en memoria.
        # Cuando armes el LoteTemporal, lo vas a persistir.
        qd = self.de_fecha.date()
        self._fecha = datetime(qd.year(), qd.month(), qd.day())
        QMessageBox.information(self, "Fecha", f"Fecha asignada: {qd.toString('dd/MM/yyyy')}")
