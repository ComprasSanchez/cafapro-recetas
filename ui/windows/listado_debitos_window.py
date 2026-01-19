from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate, QSignalBlocker
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QDateEdit, QFrame, QSizePolicy, QWidget
)

from app.db.session import session_scope
from app.service.estado_seguimiento_service import EstadoSeguimientoService
from app.service.recetas_service import RecetaService
from app.service.view_debitos import ViewDebitos


class ListadoDebitosWindow(QDialog):
    ROW_H = 38
    COMBO_H = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Débitos por recepción")
        self.setMinimumSize(1100, 650)
        self.setModal(True)

        self._estados: list[tuple[int, str]] = []
        self._build_ui()
        self._load_estados()
        self._load_recepciones()
        self._reload()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # -------------------------
        # Filters (card)
        # -------------------------
        filters_card = QFrame()
        filters_card.setObjectName("card")
        fc = QHBoxLayout(filters_card)
        fc.setContentsMargins(12, 10, 12, 10)
        fc.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(6)

        self.cb_recepcion = QComboBox()
        self.cb_recepcion.setMinimumWidth(240)
        self.cb_recepcion.setMinimumHeight(28)

        self.dt_fecha = QDateEdit()
        self.dt_fecha.setCalendarPopup(True)
        self.dt_fecha.setDisplayFormat("dd/MM/yyyy")
        self.dt_fecha.setDate(QDate.currentDate())
        self.dt_fecha.setMinimumHeight(28)
        self.dt_fecha.setFixedWidth(140)
        self.dt_fecha.setProperty("_sin_filtro", False)

        form.addRow(QLabel("Recepción:"), self.cb_recepcion)
        form.addRow(QLabel("Fecha autorización:"), self.dt_fecha)

        fc.addLayout(form, 1)

        # Right buttons
        right = QVBoxLayout()
        right.setSpacing(8)

        self.btn_reload = QPushButton("Actualizar")
        self.btn_reload.setProperty("variant", "primary")
        self.btn_reload.setMinimumHeight(32)

        self.btn_clear_fecha = QPushButton("Limpiar fecha")
        self.btn_clear_fecha.setProperty("variant", "ghost")
        self.btn_clear_fecha.setMinimumHeight(32)

        right.addWidget(self.btn_reload)
        right.addWidget(self.btn_clear_fecha)
        right.addStretch(1)

        fc.addLayout(right, 0)
        root.addWidget(filters_card, 0)

        # -------------------------
        # Table (card)
        # -------------------------
        table_card = QFrame()
        table_card.setObjectName("card")
        tc = QVBoxLayout(table_card)
        tc.setContentsMargins(12, 12, 12, 12)
        tc.setSpacing(8)

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

        # ✅ alturas para que NO se recorte el combo
        self.tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.tbl.verticalHeader().setMinimumSectionSize(self.ROW_H)

        header = self.tbl.horizontalHeader()
        header.setStretchLastSection(True)

        # Base: que Qt calcule por contenido, pero controlamos columnas largas
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        # Columnas largas => Stretch
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Débito
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Detalle

        # ✅ Columna del combo: ancho estable (mejor que stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        self.tbl.setColumnWidth(5, 260)  # ajustá a 220/260/300 si querés

        tc.addWidget(self.tbl, 1)
        root.addWidget(table_card, 1)

        # -------------------------
        # Footer
        # -------------------------
        footer = QHBoxLayout()
        footer.addStretch(1)

        btn_close = QPushButton("Cerrar")
        btn_close.setProperty("variant", "ghost")
        btn_close.setMinimumHeight(32)
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
        self.dt_fecha.setEnabled(True)
        self._reload()

    def _clear_fecha(self) -> None:
        self.dt_fecha.setProperty("_sin_filtro", True)
        self.dt_fecha.setEnabled(False)
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
            self.tbl.setRowHeight(i, self.ROW_H)

            self._set_item(i, 0, str(r.orden_lote))
            self._set_item(i, 1, str(r.nro_receta or ""))
            self._set_item(i, 2, self._fmt_money(r.importe_obs))
            self._set_item(i, 3, self._fmt_money(r.a_cargo_entidad))
            self._set_item(i, 4, str(r.descripcion_debito or ""))

            # -------------------------
            # Estado seguimiento (Combo FULL WIDTH + NO RECORTE)
            # -------------------------
            cb = QComboBox()
            cb.setMinimumHeight(self.COMBO_H)
            cb.setMaximumHeight(self.COMBO_H)
            cb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cb.setProperty("receta_id", int(r.receta_id))

            # Cargamos sin disparar cambios
            with QSignalBlocker(cb):
                cb.clear()
                for estado_id, desc in self._estados:
                    cb.addItem(desc, estado_id)

                if r.estado_seguimiento_id is not None:
                    idx = cb.findData(int(r.estado_seguimiento_id))
                    if idx >= 0:
                        cb.setCurrentIndex(idx)

            cb.setToolTip(cb.currentText())
            cb.currentTextChanged.connect(cb.setToolTip)
            cb.currentIndexChanged.connect(self._on_estado_changed)

            # Container para ocupar toda la celda + padding prolijo
            cell = QWidget()
            cell.setMinimumHeight(self.ROW_H)

            cell_l = QHBoxLayout(cell)
            cell_l.setContentsMargins(8, 4, 8, 4)  # padding (no recorta)
            cell_l.setSpacing(0)
            cell_l.addWidget(cb, 1)

            self.tbl.setCellWidget(i, 5, cell)

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
            RecetaService.update_estado_seguimiento(
                int(receta_id),
                int(new_estado_id) if new_estado_id is not None else None
            )
            self._reload()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo actualizar el estado.\n\n{e}")
            self._reload()

    # ---------------- utils ----------------
    def _set_item(self, row: int, col: int, text: str) -> None:
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.tbl.setItem(row, col, it)

    @staticmethod
    def _fmt_money(v) -> str:
        if v is None:
            return "0,00"
        try:
            return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return str(v)
