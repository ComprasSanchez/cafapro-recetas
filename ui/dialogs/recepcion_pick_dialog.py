from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
    QLineEdit, QComboBox, QCheckBox
)

from ui.usecase.recepcion_dialog_usecase import RecepcionDialogUseCase


class RecepcionPickDialog(QDialog):
    """Dialog para elegir una recepción con filtros."""

    def __init__(self, parent=None, show_closed: bool = False, enable_filter: bool = True):
        super().__init__(parent)

        self.show_closed = show_closed
        self.enable_filter = enable_filter

        self._rows = []

        self.setWindowTitle("Elegir recepción")
        self.setMinimumSize(950, 520)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # título
        title = QLabel("Seleccionar recepción")
        title.setProperty("role", "subtitle")
        root.addWidget(title)

        # -----------------------
        # filtros
        # -----------------------

        filters = QHBoxLayout()

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Buscar número...")

        self.cmb_obs = QComboBox()
        self.cmb_obs.addItem("Todas")

        self.cmb_prestador = QComboBox()
        self.cmb_prestador.addItem("Todos")

        self.cmb_estado = QComboBox()
        self.cmb_estado.addItem("Todos")

        filters.addWidget(QLabel("Buscar"))
        filters.addWidget(self.txt_search)

        filters.addWidget(QLabel("Obra social"))
        filters.addWidget(self.cmb_obs)

        filters.addWidget(QLabel("Prestador"))
        filters.addWidget(self.cmb_prestador)

        filters.addWidget(QLabel("Estado"))
        filters.addWidget(self.cmb_estado)

        filters.addStretch()

        self.chk_closed = QCheckBox("Mostrar cerradas")
        self.chk_closed.setChecked(self.show_closed)
        self.chk_closed.setEnabled(self.enable_filter)

        filters.addWidget(self.chk_closed)

        root.addLayout(filters)

        # -----------------------
        # tabla
        # -----------------------

        self.table = QTableWidget(0, 5)

        self.table.setHorizontalHeaderLabels(
            ["Número", "Obra social", "Período", "Prestador", "Estado"]
        )

        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.table.verticalHeader().setVisible(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hh.setStretchLastSection(True)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self.table)

        # -----------------------
        # botones
        # -----------------------

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setProperty("variant", "ghost")
        self.btn_cancel.setProperty("size", "md")
        self.btn_ok = QPushButton("Seleccionar")
        self.btn_ok.setProperty("variant", "primary")
        self.btn_ok.setProperty("size", "md")
        self.btn_ok.setEnabled(False)
        self.btn_ok.setDefault(True)

        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_ok)

        root.addLayout(actions)

        # -----------------------
        # eventos
        # -----------------------

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

        self.table.itemSelectionChanged.connect(self._update_ok)
        self.table.doubleClicked.connect(self.accept)

        self.txt_search.textChanged.connect(self._apply_filters)
        self.cmb_obs.currentIndexChanged.connect(self._apply_filters)
        self.cmb_prestador.currentIndexChanged.connect(self._apply_filters)
        self.cmb_estado.currentIndexChanged.connect(self._apply_filters)

        self.chk_closed.stateChanged.connect(self._reload)

        # carga inicial
        self._reload()

    # -----------------------
    # carga datos
    # -----------------------

    def _reload(self):

        try:
            self._rows = RecepcionDialogUseCase.list_recepciones(
                include_closed=self.chk_closed.isChecked(),
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudieron cargar recepciones:\n{e}")
            return

        self._load_filters()
        self._apply_filters()

    # -----------------------
    # llenar combos filtro
    # -----------------------

    def _load_filters(self):

        obs = sorted({r.obra_social for r in self._rows if r.obra_social})
        prest = sorted({r.prestador for r in self._rows if r.prestador})
        estado = sorted({r.estado for r in self._rows if r.estado})

        self.cmb_obs.blockSignals(True)
        self.cmb_prestador.blockSignals(True)
        self.cmb_estado.blockSignals(True)

        self.cmb_obs.clear()
        self.cmb_prestador.clear()
        self.cmb_estado.clear()

        self.cmb_obs.addItem("Todas")
        self.cmb_prestador.addItem("Todos")
        self.cmb_estado.addItem("Todos")

        self.cmb_obs.addItems(obs)
        self.cmb_prestador.addItems(prest)
        self.cmb_estado.addItems(estado)

        self.cmb_obs.blockSignals(False)
        self.cmb_prestador.blockSignals(False)
        self.cmb_estado.blockSignals(False)

    # -----------------------
    # aplicar filtros
    # -----------------------

    def _apply_filters(self):

        search = self.txt_search.text().lower().strip()
        obs = self.cmb_obs.currentText()
        prest = self.cmb_prestador.currentText()
        estado = self.cmb_estado.currentText()

        rows = []

        for r in self._rows:

            if search and search not in str(r.numero).lower():
                continue

            if obs != "Todas" and r.obra_social != obs:
                continue

            if prest != "Todos" and r.prestador != prest:
                continue

            if estado != "Todos" and r.estado != estado:
                continue

            rows.append(r)

        self._fill_table(rows)

    # -----------------------
    # llenar tabla
    # -----------------------

    def _fill_table(self, rows):

        self.table.setRowCount(0)

        for r in rows:

            i = self.table.rowCount()
            self.table.insertRow(i)

            it_num = QTableWidgetItem(str(r.numero))
            it_num.setData(Qt.UserRole, r.recepcion_id)
            it_num.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(i, 0, it_num)
            self.table.setItem(i, 1, QTableWidgetItem(r.obra_social))
            self.table.setItem(i, 2, QTableWidgetItem(r.periodo))
            self.table.setItem(i, 3, QTableWidgetItem(r.prestador))
            self.table.setItem(i, 4, QTableWidgetItem(r.estado))

        self._update_ok()

    # -----------------------
    # estado botón OK
    # -----------------------

    def _update_ok(self):
        self.btn_ok.setEnabled(self.selected() is not None)

    # -----------------------
    # obtener selección
    # -----------------------

    def selected(self) -> tuple[int, str] | None:

        row = self.table.currentRow()

        if row < 0:
            return None

        it = self.table.item(row, 0)

        if not it:
            return None

        rid = it.data(Qt.UserRole)

        if rid is None:
            return None

        numero = it.text()

        return int(rid), numero
