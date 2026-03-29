from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QCompleter, QLineEdit
)

from ui.usecase.recepciones_windows_usecase import RecepcionesWindowsUseCase


def fmt_fecha_ymd(v) -> str:
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return str(v)[:10]


def fmt_money_ar(v) -> str:
    if v is None:
        v = 0
    try:
        n = Decimal(str(v))
    except Exception:
        return str(v)

    s = f"{n:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


class ResumenRecepcionWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recepciones por período")
        self.setMinimumSize(1200, 650)
        self.setModal(True)

        self._periodo_id: int | None = None
        self._prestador_id: int | None = None
        self._recepcion_id: int | None = None

        self._build_ui()
        self._load_periodos()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.addWidget(QLabel("Período:"))

        self.cmb_periodo = QComboBox()
        self.cmb_periodo.setEditable(True)
        self.cmb_periodo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_periodo.setMinimumWidth(320)
        self.cmb_periodo.currentIndexChanged.connect(self._on_periodo_changed)
        top.addWidget(self.cmb_periodo)

        top.addStretch(1)
        root.addLayout(top)

        main_split = QSplitter(Qt.Horizontal)

        self.tbl_prestadores = QTableWidget(0, 4)
        self.tbl_prestadores.setHorizontalHeaderLabels(["Prestador", "Total", "A cargo OBS", "A cargo Afiliado"])
        self.tbl_prestadores.verticalHeader().setVisible(False)
        self.tbl_prestadores.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_prestadores.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_prestadores.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_prestadores.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tbl_prestadores.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_prestadores.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_prestadores.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_prestadores.itemSelectionChanged.connect(self._on_prestador_selected)

        main_split.addWidget(self.tbl_prestadores)

        right_split = QSplitter(Qt.Vertical)

        self.tbl_recepciones = QTableWidget(0, 3)
        self.tbl_recepciones.setHorizontalHeaderLabels(["Recepción", "Obra social", "Fecha"])
        self.tbl_recepciones.verticalHeader().setVisible(False)
        self.tbl_recepciones.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_recepciones.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl_recepciones.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_recepciones.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recepciones.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tbl_recepciones.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_recepciones.itemSelectionChanged.connect(self._on_recepcion_selected)
        right_split.addWidget(self.tbl_recepciones)

        self.tbl_resumen = QTableWidget(0, 4)
        self.tbl_resumen.setHorizontalHeaderLabels(["Cant. recetas", "Total bruto", "Total cargo OBS", "Total a cargo Afiliado"])
        self.tbl_resumen.verticalHeader().setVisible(False)
        self.tbl_resumen.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_resumen.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl_resumen.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_split.addWidget(self.tbl_resumen)

        main_split.addWidget(right_split)

        main_split.setStretchFactor(0, 2)
        main_split.setStretchFactor(1, 3)
        right_split.setStretchFactor(0, 2)
        right_split.setStretchFactor(1, 1)

        root.addWidget(main_split)

    def _load_periodos(self):
        try:
            self.cmb_periodo.currentIndexChanged.disconnect(self._on_periodo_changed)
        except Exception:
            pass

        periodos = RecepcionesWindowsUseCase.list_periodos()

        self.cmb_periodo.blockSignals(True)
        self.cmb_periodo.clear()

        model = QStandardItemModel(self)

        for p in periodos:
            txt = f"{p.anio}-{p.mes:02d} Q{p.quincena}"
            self.cmb_periodo.addItem(txt, p.periodo_id)

            it = QStandardItem(txt)
            it.setData(p.periodo_id, Qt.UserRole)
            model.appendRow(it)

        proxy = QSortFilterProxyModel(self)
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setFilterKeyColumn(0)

        completer = QCompleter(proxy, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        def on_text_changed(text: str):
            proxy.setFilterFixedString(text)

        le = self.cmb_periodo.lineEdit()
        if le is not None:
            le: QLineEdit
            if not hasattr(self, "_periodo_text_signal_connected"):
                le.textChanged.connect(on_text_changed)
                self._periodo_text_signal_connected = True

        self.cmb_periodo.setCompleter(completer)
        self.cmb_periodo.setCurrentIndex(-1)
        self.cmb_periodo.setEditText("")
        self.cmb_periodo.blockSignals(False)

        self._periodo_id = None
        self._prestador_id = None
        self._recepcion_id = None
        self._clear_table(self.tbl_prestadores)
        self._clear_table(self.tbl_recepciones)
        self._clear_table(self.tbl_resumen)

        self.cmb_periodo.currentIndexChanged.connect(self._on_periodo_changed)

    def _on_periodo_changed(self):
        self._periodo_id = self.cmb_periodo.currentData()
        self._prestador_id = None
        self._recepcion_id = None

        self._clear_table(self.tbl_recepciones)
        self._clear_table(self.tbl_resumen)

        if not self._periodo_id:
            self._clear_table(self.tbl_prestadores)
            return

        rows = RecepcionesWindowsUseCase.list_prestadores_resumen(
            periodo_id=int(self._periodo_id),
        )

        self.tbl_prestadores.setRowCount(len(rows))
        for i, it in enumerate(rows):
            self._set_cell(self.tbl_prestadores, i, 0, it.prestador, user_data=it.prestador_id)
            self._set_cell(self.tbl_prestadores, i, 1, fmt_money_ar(it.total_bruto), align_right=True)
            self._set_cell(self.tbl_prestadores, i, 2, fmt_money_ar(it.total_cobertura), align_right=True)
            self._set_cell(self.tbl_prestadores, i, 3, fmt_money_ar(it.total_afiliado), align_right=True)

        if rows:
            self.tbl_prestadores.selectRow(0)

    def _on_prestador_selected(self):
        row = self._selected_row(self.tbl_prestadores)
        if row is None:
            return

        prestador_id = self.tbl_prestadores.item(row, 0).data(Qt.UserRole)
        if not prestador_id or not self._periodo_id:
            return

        self._prestador_id = int(prestador_id)
        self._recepcion_id = None
        self._clear_table(self.tbl_recepciones)
        self._clear_table(self.tbl_resumen)

        receps = RecepcionesWindowsUseCase.list_recepciones_resumen(
            periodo_id=int(self._periodo_id),
            prestador_id=int(self._prestador_id),
        )

        self.tbl_recepciones.setRowCount(len(receps))
        for i, r in enumerate(receps):
            self._set_cell(self.tbl_recepciones, i, 0, str(r.numero), user_data=r.recepcion_id)
            self._set_cell(self.tbl_recepciones, i, 1, r.obra_social or "")
            fecha_txt = fmt_fecha_ymd(r.fecha_presentacion)
            self._set_cell(self.tbl_recepciones, i, 2, fecha_txt)

        if receps:
            self.tbl_recepciones.selectRow(0)

    def _on_recepcion_selected(self):
        row = self._selected_row(self.tbl_recepciones)
        if row is None:
            return

        recepcion_id = self.tbl_recepciones.item(row, 0).data(Qt.UserRole)
        if not recepcion_id:
            return

        self._recepcion_id = int(recepcion_id)

        res = RecepcionesWindowsUseCase.get_resumen_recepcion(
            recepcion_id=self._recepcion_id,
        )

        self._clear_table(self.tbl_resumen)

        if not res:
            return

        self.tbl_resumen.setRowCount(1)
        self._set_cell(self.tbl_resumen, 0, 0, str(res.cantidad_recetas))
        self._set_cell(self.tbl_resumen, 0, 1, fmt_money_ar(res.total_bruto), align_right=True)
        self._set_cell(self.tbl_resumen, 0, 2, fmt_money_ar(res.total_cobertura), align_right=True)
        self._set_cell(self.tbl_resumen, 0, 3, fmt_money_ar(res.total_afiliado), align_right=True)

    @staticmethod
    def _clear_table(tbl: QTableWidget):
        tbl.setRowCount(0)

    @staticmethod
    def _selected_row(tbl: QTableWidget) -> int | None:
        sel = tbl.selectionModel().selectedRows()
        return sel[0].row() if sel else None

    @staticmethod
    def _set_cell(tbl: QTableWidget, row: int, col: int, text: str, user_data=None, *, align_right: bool = False):
        it = QTableWidgetItem(text)
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)

        if user_data is not None:
            it.setData(Qt.UserRole, user_data)

        if align_right:
            it.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))

        tbl.setItem(row, col, it)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_periodos()
        self.cmb_periodo.setCurrentIndex(-1)
        self.cmb_periodo.setEditText("")
