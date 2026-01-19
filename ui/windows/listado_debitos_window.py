from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, QSignalBlocker
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDateEdit
)

from app.db.session import session_scope
from app.service.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas_service import RecetaService
from app.service.view_debitos import ViewDebitos


class ListadoDebitosWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Débitos por recepción")
        self.setMinimumSize(1100, 650)
        self.setModal(True)

        self._estados = []  # [(id, descripcion)]
        self._build_ui()
        self._load_estados()
        self._load_recepciones()
        self._reload()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # filtros
        filters = QHBoxLayout()
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)

        self.cb_recepcion = QComboBox()
        self.cb_recepcion.setMinimumWidth(220)

        self.dt_fecha = QDateEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDisplayFormat("dd/MM/yyyy")
        self.dt_fecha.setDate(QDate.currentDate())
        self.dt_fecha.setProperty("_sin_filtro", False)

        self.btn_clear_fecha = QPushButton("Limpiar fecha")
        self.btn_reload = QPushButton("Actualizar")

        form.addRow(QLabel("Recepción:"), self.cb_recepcion)
        form.addRow(QLabel("Fecha autorización:"), self.dt_fecha)

        filters.addLayout(form)
        filters.addStretch(1)

        right = QVBoxLayout()
        right.addWidget(self.btn_reload)
        right.addWidget(self.btn_clear_fecha)
        right.addStretch(1)
        filters.addLayout(right)

        root.addLayout(filters)

        # tabla
        self.tbl = QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels([
            "Orden lote", "N° receta", "Importe OBS", "A cargo entidad",
            "Débito", "Estado seguimiento", "Detalle"
        ])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(False)

        header = self.tbl.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)

        root.addWidget(self.tbl, 1)

        # footer
        footer = QHBoxLayout()
        footer.addStretch(1)
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        footer.addWidget(btn_close)
        root.addLayout(footer)

        # signals
        self.cb_recepcion.currentIndexChanged.connect(self._reload)
        self.dt_fecha.dateChanged.connect(self._on_fecha_changed)
        self.btn_reload.clicked.connect(self._reload)
        self.btn_clear_fecha.clicked.connect(self._clear_fecha)

    # ---------------- data loaders ----------------
    def _load_estados(self) -> None:
        with session_scope() as s:
            rows = EstadoSeguimientoService.list(s)
        self._estados = [(int(r.estado_seguimiento_id), str(r.descripcion)) for r in rows]

    def _load_recepciones(self) -> None:
        receps = ViewDebitos.list_recepciones()
        with QSignalBlocker(self.cb_recepcion):
            self.cb_recepcion.clear()
            self.cb_recepcion.addItem("Todas", None)
            for rid in receps:
                self.cb_recepcion.addItem(str(rid), rid)

    # ---------------- filters helpers ----------------
    def _on_fecha_changed(self) -> None:
        self.dt_fecha.setProperty("_sin_filtro", False)
        self._reload()

    def _clear_fecha(self) -> None:
        self.dt_fecha.setProperty("_sin_filtro", True)
        self._reload()

    def _get_fecha_filtro(self) -> date | None:
        if self.dt_fecha.property("_sin_filtro") is True:
            return None
        qd = self.dt_fecha.date()
        return date(qd.year(), qd.month(), qd.day())

    # ---------------- render ----------------
    def _reload(self) -> None:
        recepcion_id = self.cb_recepcion.currentData()
        fecha = self._get_fecha_filtro()

        try:
            rows = ViewDebitos.list_debitos(
                recepcion_id=recepcion_id,
                fecha_autorizacion=fecha,
            )
            self._render(rows)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar los débitos.\n\n{e}")

    def _render(self, rows) -> None:
        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            # 0 orden_lote
            self._set_item(i, 0, str(r.orden_lote))

            # 1 nro_receta
            self._set_item(i, 1, str(r.nro_receta or ""))

            # 2 importe_obs
            self._set_item(i, 2, self._fmt_money(r.importe_obs))

            # 3 a_cargo_entidad
            self._set_item(i, 3, self._fmt_money(r.a_cargo_entidad))

            # 4 descripcion_debito
            self._set_item(i, 4, str(r.descripcion_debito or ""))

            # 5 estado_seguimiento (editable)
            cb = QComboBox()
            cb.setMinimumWidth(200)
            cb.setProperty("receta_id", int(r.receta_id))

            for estado_id, desc in self._estados:
                cb.addItem(desc, estado_id)

            if r.estado_seguimiento_id is not None:
                idx = cb.findData(int(r.estado_seguimiento_id))
                if idx >= 0:
                    cb.setCurrentIndex(idx)

            cb.currentIndexChanged.connect(self._on_estado_changed)
            self.tbl.setCellWidget(i, 5, cb)

            # 6 detalle
            self._set_item(i, 6, str(r.detalle or ""))

    def _on_estado_changed(self) -> None:
        cb = self.sender()
        if not isinstance(cb, QComboBox):
            return

        receta_id = cb.property("receta_id")
        new_estado_id = cb.currentData()

        if receta_id is None:
            return

        try:
            RecetaService.update_estado_seguimiento(int(receta_id), int(new_estado_id) if new_estado_id is not None else None)
            self._reload()  # refresca siempre al cambiar
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el estado.\n\n{e}")
            self._reload()

    # ---------------- utils ----------------
    def _set_item(self, row: int, col: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.tbl.setItem(row, col, it)

    def _fmt_money(self, v) -> str:
        if v is None:
            return "0,00"
        try:
            return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(v)
