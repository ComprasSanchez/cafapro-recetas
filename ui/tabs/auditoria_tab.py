from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QPixmap, QColor, QPen, QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QComboBox, QCheckBox, QMenu, QApplication, QStyle,
    QStyledItemDelegate,
)

from app.db.session import session_scope
from app.service.recetas.asociacion_service import AsociacionService
from app.service.recetas.recetas_service import RecetaService
from ui.dialogs.forzar_asocaicion_dialog import ForzarAsociacionDialog
from ui.dialogs.numero_receta_dialog import NumeroRecetaDialog
from ui.dialogs.reasociar_reeta_dialog import ReasociarRecetaDialog
from ui.models.auditoria_row_vm import AuditoriaRowVM
from ui.tabs.base_tab import BaseTabWidget
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.auditoria_visual_dialog import AuditoriaVisualDialog

from ui.usecase.auditoria_usecase import (
    AuditoriaUseCase, RecepcionOut, EstadosOut, AuditoriaRowsOut, PreviewBytesOut
)


class RowOutlineDelegate(QStyledItemDelegate):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table
        self._pen = QPen(QColor(75, 85, 99))
        self._pen.setWidth(1)

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)

        active_row = getattr(self._table, "_active_row", -1)
        if active_row < 0 or index.row() != active_row:
            return

        model = self._table.model()
        if model is None:
            return

        visible_columns = [c for c in range(model.columnCount()) if not self._table.isColumnHidden(c)]
        if not visible_columns:
            return

        first_col = visible_columns[0]
        last_col = visible_columns[-1]

        if index.column() != first_col:
            return

        first_idx = model.index(index.row(), first_col)
        first_rect = self._table.visualRect(first_idx)
        right_idx = model.index(index.row(), last_col)
        right_rect = self._table.visualRect(right_idx)

        row_left = first_rect.left()
        row_top = first_rect.top()
        row_bottom = first_rect.bottom() - 1
        row_right = right_rect.right() - 1

        painter.save()
        painter.setPen(self._pen)
        painter.drawLine(row_left, row_top, row_right, row_top)
        painter.drawLine(row_left, row_bottom, row_right, row_bottom)

        painter.restore()


class AuditoriaTab(BaseTabWidget):
    ROW_H = 32  # un toque más compacta

    COL_RECETA = 0
    COL_REF = 1
    COL_LOTE = 2
    COL_RECETA_OK = 3
    COL_ARCHIVO_OK = 4
    COL_RECON = 5
    COL_OFI = 6
    COL_ESTADO = 7
    COL_DEBITOS = 8
    COL_ARCHIVOS = 9

    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._rows_view: list = []
        self._last_preview_path: str | None = None
        self._active_row: int = -1
        self._active_marker_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
        self._empty_icon = QIcon()

        self._uc = AuditoriaUseCase()

        # evita que se dispare preview mientras re-renderizamos
        self._rendering_table = False

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_header(), 0)
        root.addWidget(self._build_body(), 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

        # cargar estados async (no bloquea)
        self.run_job(
            self._uc.load_estados,
            title="Cargando estados…",
            on_result=self._apply_estados,
            on_error=lambda err: None,
        )

    # -------------------------
    # HEADER
    # -------------------------
    @staticmethod
    def _ro_line(text: str = "-") -> QLineEdit:
        le = QLineEdit(text)
        le.setReadOnly(True)
        le.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        le.setMinimumHeight(28)
        le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return le

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("card")
        header.setMaximumHeight(130)

        grid = QGridLayout(header)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        lb_num = QLabel("N° Recepción:")
        self.in_numero = self._ro_line("-")
        self.in_numero.setFixedWidth(140)

        self.btn_pick_recepcion = QPushButton("…")
        self.btn_pick_recepcion.setFixedSize(32, 28)
        self.btn_pick_recepcion.clicked.connect(self._on_pick_recepcion)

        self.btn_visual = QPushButton("Auditoría visual")
        self.btn_visual.setProperty("variant", "primary")
        self.btn_visual.setMinimumHeight(32)
        self.btn_visual.setEnabled(False)
        self.btn_visual.clicked.connect(self._on_open_auditoria_visual)

        self.btn_reload = QPushButton()
        self.btn_reload.setToolTip("Recargar auditoría")
        self.btn_reload.setMinimumHeight(32)

        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.btn_reload.setIcon(icon)

        self.btn_reload.clicked.connect(self._reload_auditoria)

        num_box = QWidget()
        num_l = QHBoxLayout(num_box)
        num_l.setContentsMargins(0, 0, 0, 0)
        num_l.setSpacing(6)
        num_l.addWidget(self.in_numero, 0)
        num_l.addWidget(self.btn_pick_recepcion, 0)

        row0_box = QWidget()
        row0_l = QHBoxLayout(row0_box)
        row0_l.setContentsMargins(0, 0, 0, 0)
        row0_l.setSpacing(10)
        row0_l.addWidget(num_box, 0)
        row0_l.addWidget(self.btn_visual, 0)
        row0_l.addWidget(self.btn_reload, 0)
        row0_l.addStretch(1)

        lb_obs = QLabel("Obra social:")
        self.in_obs = self._ro_line("-")
        self.in_obs.setFixedWidth(240)

        lb_prest = QLabel("Prestador:")
        self.in_prestador = self._ro_line("-")
        self.in_prestador.setFixedWidth(280)

        row1_box = QWidget()
        row1_l = QHBoxLayout(row1_box)
        row1_l.setContentsMargins(0, 0, 0, 0)
        row1_l.setSpacing(10)
        row1_l.addWidget(self.in_obs, 0)
        row1_l.addSpacing(8)
        row1_l.addWidget(lb_prest, 0)
        row1_l.addWidget(self.in_prestador, 0)
        row1_l.addStretch(1)

        lb_periodo = QLabel("Período:")
        self.in_periodo = self._ro_line("-")
        self.in_periodo.setFixedWidth(160)

        lb_quinc = QLabel("Quincena:")
        self.in_quincena = self._ro_line("-")
        self.in_quincena.setFixedWidth(80)
        self.in_quincena.setAlignment(Qt.AlignCenter)

        row2_box = QWidget()
        row2_l = QHBoxLayout(row2_box)
        row2_l.setContentsMargins(0, 0, 0, 0)
        row2_l.setSpacing(10)
        row2_l.addWidget(self.in_periodo, 0)
        row2_l.addWidget(lb_quinc, 0)
        row2_l.addWidget(self.in_quincena, 0)
        row2_l.addStretch(1)

        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        grid.addWidget(lb_num, 0, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(row0_box, 0, 1)

        grid.addWidget(lb_obs, 1, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(row1_box, 1, 1)

        grid.addWidget(lb_periodo, 2, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(row2_box, 2, 1)

        return header

    def _on_pick_recepcion(self) -> None:
        dlg = RecepcionPickDialog(self, show_closed=False, enable_filter=True)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        rid = dlg.selected()[0]
        if not rid:
            return

        self.run_job(
            self._uc.load_recepcion,
            recepcion_id=rid,
            title="Cargando recepción…",
            on_result=self._apply_recepcion,
            on_error=self._ui_error,
        )

    def _apply_recepcion(self, out: RecepcionOut) -> None:
        self._recepcion_id = out.recepcion_id

        self.in_numero.setText(out.numero)
        self.in_prestador.setText(out.prestador)
        self.in_obs.setText(out.obra_social)

        self.in_periodo.setText(out.periodo)
        quincena = "-"
        if "Q1" in out.periodo:
            quincena = "1ª"
        elif "Q2" in out.periodo:
            quincena = "2ª"
        self.in_quincena.setText(quincena)

        self._rows_view = []
        self._clear_table_and_preview()

        self.run_job(
            self._uc.load_auditoria,
            recepcion_id=self._recepcion_id,
            title="Cargando auditoría…",
            on_result=self._apply_auditoria_rows,
            on_error=self._ui_error,
        )

    # -------------------------
    # BODY
    # -------------------------
    def _build_body(self) -> QFrame:
        body = QFrame()
        body.setObjectName("card")

        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

        self.lb_status = QLabel("Seleccioná una recepción para cargar la auditoría.")
        self.lb_status.setObjectName("muted")
        lay.addWidget(self.lb_status, 0)

        lay.addWidget(self._build_filters(), 0)

        split = QSplitter(Qt.Orientation.Horizontal)
        lay.addWidget(split, 1)

        # -------- IZQ: TABLA --------
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(0)

        self.tbl = QTableWidget(0, 10)
        self.tbl.setObjectName("auditoria_rows_table")
        self.tbl.setHorizontalHeaderLabels([
            "Receta", "Referencia", "Lote",
            "Receta OK", "Archivo OK",
            "Reconocido", "Oficial", "Estado",
            "Débitos", "Archivo"
        ])

        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.tbl.verticalHeader().setMinimumSectionSize(self.ROW_H)
        self.tbl.setWordWrap(False)
        self.tbl.setStyleSheet(
            "QTableWidget#auditoria_rows_table {"
            " selection-background-color: transparent;"
            " selection-color: #111827;"
            " outline: none;"
            "}"
            "QTableWidget#auditoria_rows_table::item:selected,"
            "QTableWidget#auditoria_rows_table::item:selected:active,"
            "QTableWidget#auditoria_rows_table::item:selected:!active {"
            " background: transparent;"
            " color: #111827;"
            " border: none;"
            " outline: none;"
            "}"
            "QTableWidget#auditoria_rows_table::item:focus {"
            " outline: none;"
            " border: 0px;"
            " background-color:transparent;"
            "}"
        )
        self.tbl.setItemDelegate(RowOutlineDelegate(self.tbl))
        self.tbl.installEventFilter(self)

        self.tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tbl.customContextMenuRequested.connect(self._show_row_menu)

        hh = self.tbl.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setMinimumSectionSize(60)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 🔥 MODO HÍBRIDO CORRECTO
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # Usuario puede redimensionar
        hh.setStretchLastSection(True)  # Última columna absorbe espacio
        hh.setSectionsMovable(True)  # Permite mover columnas

        # Tamaños iniciales (opcional, solo como punto de partida)
        hh.resizeSection(self.COL_RECETA, 120)
        hh.resizeSection(self.COL_REF, 170)
        hh.resizeSection(self.COL_LOTE, 70)
        hh.resizeSection(self.COL_RECETA_OK, 90)
        hh.resizeSection(self.COL_ARCHIVO_OK, 90)
        hh.resizeSection(self.COL_RECON, 90)
        hh.resizeSection(self.COL_OFI, 90)
        hh.resizeSection(self.COL_ESTADO, 80)
        hh.resizeSection(self.COL_DEBITOS, 80)

        hh.setContextMenuPolicy(Qt.CustomContextMenu)
        hh.customContextMenuRequested.connect(self._show_column_menu)

        self.tbl.cellClicked.connect(self._on_cell_clicked)
        self.tbl.currentCellChanged.connect(self._on_current_cell_changed)

        left_l.addWidget(self.tbl, 1)
        split.addWidget(left)

        # -------- DER: PREVIEW --------
        right = QFrame()
        right.setObjectName("panel")
        rp_l = QVBoxLayout(right)
        rp_l.setContentsMargins(8, 8, 8, 8)
        rp_l.setSpacing(8)

        title = QLabel("Vista previa")
        title.setProperty("role", "subtitle")
        rp_l.addWidget(title, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.img_preview = QLabel("Sin imagen")
        self.img_preview.setAlignment(Qt.AlignCenter)
        self.img_preview.setScaledContents(False)

        self.scroll.setWidget(self.img_preview)
        rp_l.addWidget(self.scroll, 1)

        right.setMinimumWidth(380)
        right.setMaximumWidth(520)
        split.addWidget(right)

        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 2)

        return body

    def _build_filters(self) -> QFrame:
        bar = QFrame()
        l = QHBoxLayout(bar)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)

        l.addWidget(QLabel("Buscar:"))

        self.in_search = QLineEdit()
        self.in_search.setPlaceholderText("N° receta o referencia…")
        self.in_search.setMinimumHeight(28)
        self.in_search.setMinimumWidth(220)
        self.in_search.textChanged.connect(self._on_search_changed)
        l.addWidget(self.in_search, 0)

        l.addWidget(QLabel("Estado:"))
        self.cb_estado = QComboBox()
        self.cb_estado.setMinimumHeight(28)
        self.cb_estado.setMinimumWidth(240)
        self.cb_estado.addItem("Cargando…", None)
        self.cb_estado.currentIndexChanged.connect(self._apply_filters)
        l.addWidget(self.cb_estado, 0)

        l.addWidget(QLabel("Débitos:"))
        self.cb_debitos = QComboBox()
        self.cb_debitos.setMinimumHeight(28)
        self.cb_debitos.setMinimumWidth(170)
        self.cb_debitos.addItem("Todos", None)
        self.cb_debitos.addItem("Con débitos", True)
        self.cb_debitos.addItem("Sin débitos", False)
        self.cb_debitos.currentIndexChanged.connect(self._apply_filters)
        l.addWidget(self.cb_debitos, 0)

        self.chk_diff_montos = QCheckBox("Solo diferencias $")
        self.chk_diff_montos.toggled.connect(self._apply_filters)
        l.addWidget(self.chk_diff_montos, 0)

        self.lb_filtered = QLabel("")
        self.lb_filtered.setObjectName("muted")
        l.addWidget(self.lb_filtered, 0)

        l.addStretch(1)
        return bar

    def _show_column_menu(self, pos):
        menu = QMenu(self)

        for col in range(self.tbl.columnCount()):
            col_name = self.tbl.horizontalHeaderItem(col).text()
            action = menu.addAction(col_name)
            action.setCheckable(True)
            action.setChecked(not self.tbl.isColumnHidden(col))

            # capturar col correctamente
            action.triggered.connect(lambda checked, c=col: self.tbl.setColumnHidden(c, not checked))

        menu.exec(self.tbl.horizontalHeader().mapToGlobal(pos))

    def _show_row_menu(self, pos):

        item = self.tbl.itemAt(pos)

        if not item:
            return

        row = item.row()
        self._set_active_row(row)

        receta_item = self.tbl.item(row, self.COL_RECETA)
        ref_item = self.tbl.item(row, self.COL_REF)

        receta = receta_item.text() if receta_item else ""
        referencia = ref_item.text() if ref_item else ""

        data = receta_item.data(Qt.UserRole) or {}

        receta_id = data.get("receta_id")
        estado_id = data.get("estado_id")
        asociacion_id = data.get("asociacion_id")

        menu = QMenu(self)

        if receta and estado_id != 3:
            act_copy_receta = menu.addAction(f"Copiar N° Receta ({receta})")
            act_copy_receta.triggered.connect(
                lambda: QApplication.clipboard().setText(receta)
            )

        if referencia and estado_id != 3:
            act_copy_ref = menu.addAction(f"Copiar N° Referencia ({referencia})")
            act_copy_ref.triggered.connect(
                lambda: QApplication.clipboard().setText(referencia)
            )

        if estado_id == 3 and receta_id:
            act_forzar = menu.addAction("Forzar asociación")
            act_forzar.triggered.connect(
                lambda: self._open_forzar_asociacion(receta_id)
            )

            act_anular = menu.addAction("Anular receta")
            act_anular.triggered.connect(
                lambda: self._anular_receta(receta_id)
            )

            act_dup = menu.addAction("Marcar como duplicada")
            act_dup.triggered.connect(
                lambda: self._duplicar_receta(receta_id)
            )

            act_del = menu.addAction("Eliminar / Sobrante")
            act_del.triggered.connect(
                lambda: self._eliminar_sobrante(receta_id)
            )

            act_reasociar = menu.addAction("Reasociar receta")

            act_reasociar.triggered.connect(
                lambda: self._open_reasociar_receta(receta_id)
            )

        if asociacion_id and estado_id == 2:
            menu.addSeparator()

            act_desasociar = menu.addAction("Desasociar receta")
            act_desasociar.setProperty("danger", True)

            act_desasociar.triggered.connect(
                lambda: self._desasociar_receta(receta_id)
            )

        menu.exec(self.tbl.mapToGlobal(pos))

    # -------------------------
    # Estados / Auditoría
    # -------------------------
    def _apply_estados(self, out: EstadosOut) -> None:
        self.cb_estado.blockSignals(True)
        self.cb_estado.clear()

        self.cb_estado.addItem("Todos", None)
        self.cb_estado.addItem("Sin asociación", "SIN_ASOC")

        for eid, desc in out.estados:
            self.cb_estado.addItem(str(desc), int(eid))

        self.cb_estado.blockSignals(False)

    def _apply_auditoria_rows(self, out: AuditoriaRowsOut) -> None:
        self._rows_view = self._map_rows(out.rows)
        self.lb_status.setText(f"Auditoría cargada: {len(self._rows_view)} registros")
        self._apply_filters()

    # -------------------------
    # Filters (en memoria)
    # -------------------------
    @staticmethod
    def _estado_id(r) -> int:
        return int(getattr(r, "estado_receta_id", 0) or 0)

    def _apply_filters(self) -> None:
        base_rows = self._rows_view or []
        total = len(base_rows)
        search_txt = (self.in_search.text().strip().lower() if hasattr(self, "in_search") else "")

        estado_sel = self.cb_estado.currentData() if hasattr(self, "cb_estado") else None
        debitos_flag = self.cb_debitos.currentData() if hasattr(self, "cb_debitos") else None
        only_diff = self.chk_diff_montos.isChecked() if hasattr(self, "chk_diff_montos") else False

        idxs = list(range(total))

        if estado_sel is not None:

            if estado_sel == "SIN_ASOC":
                idxs = [i for i in idxs if base_rows[i].asociacion_id is None]

            else:
                sid = int(estado_sel)
                idxs = [
                    i for i in idxs
                    if self._estado_id(base_rows[i]) == sid
                       and (
                               sid not in (1, 2)  # estados que NO requieren asociación
                               or getattr(base_rows[i], "asociacion_id", None) is not None
                       )
                ]

        if debitos_flag is not None:
            want = bool(debitos_flag)
            idxs = [i for i in idxs if bool(getattr(base_rows[i], "flag_debitos", False)) == want]

        if only_diff:
            def is_diff(i: int) -> bool:
                r = base_rows[i]
                rec = float(getattr(r, "importe_reconocido", 0) or 0)
                ofi = float(getattr(r, "importe_oficial", 0) or 0)
                return abs(rec - ofi) > 0.009

            idxs = [i for i in idxs if is_diff(i)]

        if search_txt:
            idxs = [
                i for i in idxs
                if search_txt in str(getattr(base_rows[i], "numero_receta", "")).lower()
                   or search_txt in str(getattr(base_rows[i], "numero_referencia", "")).lower()
            ]

        rows = [base_rows[i] for i in idxs]
        self._render_table(rows)
        self.lb_filtered.setText(f"Mostrando {len(rows)} de {total}")

    def _render_table(self, rows):

        self._rendering_table = True
        self.tbl.setUpdatesEnabled(False)

        try:

            self.tbl.setSortingEnabled(False)
            self.tbl.setRowCount(len(rows))

            for i, r in enumerate(rows):
                self._render_row(i, r)

            self.tbl.setSortingEnabled(True)
            self.tbl.clearSelection()
            self._set_active_row(-1)
            self._clear_preview()

        finally:

            self.tbl.setUpdatesEnabled(True)
            self._rendering_table = False

    def _set_item(self, row: int, col: int, text: str, align: Qt.AlignmentFlag | None = None) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignVCenter | (align if align is not None else Qt.AlignLeft))
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable & ~Qt.ItemFlag.ItemIsSelectable)
        self.tbl.setItem(row, col, it)

    # -------------------------
    # Selection -> Preview
    # -------------------------
    def _set_active_row(self, row: int) -> None:
        if row < 0 or row >= self.tbl.rowCount():
            row = -1

        if self._active_row == row:
            return

        old_row = self._active_row
        if old_row >= 0:
            self._paint_active_row(old_row, active=False)

        self._active_row = row
        if self._active_row >= 0:
            self._paint_active_row(self._active_row, active=True)

        self.tbl.viewport().update()

    def _paint_active_row(self, row: int, *, active: bool) -> None:
        if row < 0 or row >= self.tbl.rowCount():
            return

        for col in range(self.tbl.columnCount()):
            it = self.tbl.item(row, col)
            if not it:
                continue

            font = it.font()
            font.setBold(active)
            it.setFont(font)

            if col == self.COL_RECETA:
                it.setIcon(self._active_marker_icon if active else self._empty_icon)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        self._set_active_row(row)

        c0 = self.tbl.item(row, self.COL_RECETA)
        if not c0:
            self._clear_preview()
            self._sync_visual_button_state()
            return

        self._on_item_clicked(c0)

    def _on_current_cell_changed(self, current_row: int, _current_col: int, _prev_row: int, _prev_col: int) -> None:
        if self._rendering_table:
            return

        self._set_active_row(current_row)
        self._sync_visual_button_state()

        if current_row < 0:
            self._clear_preview()
            return

        it = self.tbl.item(current_row, self.COL_RECETA)
        if not it:
            self._clear_preview()
            return

        self._on_item_clicked(it)

    def eventFilter(self, obj, event):
        if obj is getattr(self, "tbl", None) and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                row_count = self.tbl.rowCount()
                if row_count <= 0:
                    return True

                current_row = self._active_row if self._active_row >= 0 else self.tbl.currentRow()
                if current_row < 0:
                    current_row = 0

                step = -1 if key == Qt.Key.Key_Up else 1
                new_row = max(0, min(row_count - 1, current_row + step))

                self.tbl.setCurrentCell(new_row, self.COL_RECETA)

                it = self.tbl.item(new_row, self.COL_RECETA)
                if it:
                    self.tbl.scrollToItem(it, QAbstractItemView.ScrollHint.PositionAtCenter)

                return True

        return super().eventFilter(obj, event)

    # -------------------------
    # Preview async
    # -------------------------
    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        c0 = self.tbl.item(row, self.COL_RECETA)
        if not c0:
            return

        data = c0.data(Qt.UserRole) or {}
        raw = (data.get("frente") or "").strip()
        if not raw:
            self._clear_preview()
            self._last_preview_path = None
            self._sync_visual_button_state()
            return

        src = self._uc.resolve_preview_src(raw)

        self._last_preview_path = src

        self._load_preview_async(src)

        self._sync_visual_button_state()

    def _load_preview_async(self, path: str) -> None:
        vw = max(200, self.scroll.viewport().width() - 12)
        vh = max(200, self.scroll.viewport().height() - 12)

        self.img_preview.setText("Cargando…")
        self.img_preview.setPixmap(QPixmap())

        self.run_job(
            self._uc.load_preview_bytes,
            path=path,
            vw=vw,
            vh=vh,
            title="Cargando imagen…",
            on_result=self._apply_preview_bytes,
            on_error=self._ui_error_preview,
        )

    def _apply_preview_bytes(self, out: PreviewBytesOut) -> None:
        if self._last_preview_path and (self._last_preview_path != out.path):
            return

        img = out.img_bytes
        if callable(img):
            img = img()

        pix = QPixmap()
        pix.loadFromData(img)

        self.img_preview.setPixmap(pix)
        self.img_preview.resize(pix.size())
        self.img_preview.setText("")

    def _clear_preview(self) -> None:
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText("Sin imagen")
        self._last_preview_path = None
        self.btn_visual.setEnabled(False)

    def _clear_table_and_preview(self) -> None:
        self.tbl.setRowCount(0)
        self.lb_status.setText("Cargando auditoría…")
        self.lb_filtered.setText("")
        self._clear_preview()

    def resize_event(self, event) -> None:
        super().resizeEvent(event)
        if self._last_preview_path:
            self._load_preview_async(self._last_preview_path)

    # -------------------------
    # Auditoría visual (✅ NUEVO: abre una sola vez)
    # -------------------------
    def _sync_visual_button_state(self) -> None:
        row = self._active_row
        if row < 0:
            row = self.tbl.currentRow()

        if row < 0:
            self.btn_visual.setEnabled(False)
            return

        c0 = self.tbl.item(row, self.COL_RECETA)
        if not c0:
            self.btn_visual.setEnabled(False)
            return

        data = c0.data(Qt.UserRole) or {}
        asociacion_id = data.get("asociacion_id")

        self.btn_visual.setEnabled(bool(asociacion_id))

    def _on_open_auditoria_visual(self) -> None:
        start_row = self._active_row if self._active_row >= 0 else self.tbl.currentRow()
        if start_row < 0:
            return

        asociacion_ids: list[int] = []

        for row in range(start_row, self.tbl.rowCount()):
            c0 = self.tbl.item(row, self.COL_RECETA)
            if not c0:
                continue

            data = c0.data(Qt.UserRole) or {}
            asociacion_id = data.get("asociacion_id")

            if asociacion_id:
                asociacion_ids.append(int(asociacion_id))

        if not asociacion_ids:
            QMessageBox.warning(
                self,
                "Sin registros",
                "No hay asociaciones para auditar desde esta fila.",
            )
            return

        dlg = AuditoriaVisualDialog(
            asociacion_ids=asociacion_ids,
            start_index=0,
            parent=self,
            creado_por_usuario_id=self.creado_por_usuario_id,
        )

        dlg.exec()
        self._reload_auditoria()

    # -------------------------
    # UI error helpers
    # -------------------------
    def _ui_error(self, err_text: str) -> None:
        msg = (err_text or "").lower()
        is_not_found = ("filenotfounderror" in msg) or ("no se encontró" in msg) or ("no encontrado" in msg)

        lines = [l.strip() for l in (err_text or "").splitlines() if l.strip()]
        nice = lines[-1] if lines else err_text

        if is_not_found:
            QMessageBox.warning(self, "Atención", nice)
        else:
            QMessageBox.critical(self, "Error", err_text)

    def _ui_error_preview(self, err_text: str) -> None:
        lines = [l.strip() for l in (err_text or "").splitlines() if l.strip()]
        nice = lines[-1] if lines else err_text
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText(f"No se pudo cargar la imagen.\n{nice}")

    def _set_bg(self, row: int, col: int, color) -> None:
        it = self.tbl.item(row, col)
        if it:
            it.setBackground(color)

    @staticmethod
    def _is_diff_money(a: float, b: float, tol: float = 0.009) -> bool:
        return abs(a - b) > tol

    def _on_search_changed(self):
        self._search_timer.start(180)

    def _open_forzar_asociacion(self, receta_id: int):
        dlg = ForzarAsociacionDialog(
            recepcion_id=self._recepcion_id,
            receta_id=receta_id,
            parent=self,
        )

        if dlg.exec():
            # refrescar auditoría
            self.run_job(
                self._uc.load_auditoria,
                recepcion_id=self._recepcion_id,
                title="Actualizando auditoría...",
                on_result=self._apply_auditoria_rows,
                on_error=self._ui_error,
            )

    def _anular_receta(self, receta_id: int):
        row = self.tbl.currentRow()

        dlg = NumeroRecetaDialog(self)

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        nro_receta = dlg.numero_receta()

        if not nro_receta:
            QMessageBox.warning(self, "Atención", "Debés ingresar un número de receta.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Anular receta {nro_receta}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if resp != QMessageBox.StandardButton.Yes:
            return

        with session_scope() as s:
            RecetaService.anular_receta(
                s,
                receta_id=receta_id,
                nro_receta=nro_receta
            )

        self._reload_auditoria()

    def _duplicar_receta(self, receta_id: int):

        row = self.tbl.currentRow()

        dlg = NumeroRecetaDialog(self)

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        nro_receta = dlg.numero_receta()

        if not nro_receta:
            QMessageBox.warning(self, "Atención", "Debés ingresar un número de receta.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Marcar receta {nro_receta} como duplicada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if resp != QMessageBox.StandardButton.Yes:
            return

        with session_scope() as s:
            RecetaService.duplicar_receta(
                s,
                receta_id=receta_id,
                nro_receta=nro_receta,
            )

        self._reload_auditoria()

    def _eliminar_sobrante(self, receta_id: int):

        resp = QMessageBox.warning(
            self,
            "Eliminar receta",
            (
                f"¿Seguro que querés eliminar la receta?\n\n"
                "Esta acción eliminará también las imágenes del sistema "
                "y no se puede deshacer."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if resp != QMessageBox.StandardButton.Yes:
            return

        with session_scope() as s:
            RecetaService.eliminar_sobrante(
                s,
                receta_id=receta_id,
            )

        self._reload_auditoria()

    def _desasociar_receta(self, receta_id: int):

        resp = QMessageBox.warning(
            self,
            "Desasociar receta",
            "¿Seguro que querés desasociar la receta?\n\n"
            "Se restaurará el historial anterior.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if resp != QMessageBox.StandardButton.Yes:
            return

        with session_scope() as s:
            AsociacionService.desasociar(
                s,
                receta_id=receta_id,
            )

        self._reload_auditoria()

    @staticmethod
    def _map_rows(rows):

        mapped = []

        for r in rows:
            vm = AuditoriaRowVM(
                receta_id=getattr(r, "receta_id", None),
                asociacion_id=getattr(r, "asociacion_id", None),

                numero_receta=str(getattr(r, "numero_receta", "") or ""),
                numero_referencia=str(getattr(r, "numero_referencia", "") or ""),
                nro_lote=str(getattr(r, "nro_lote", "") or ""),

                existe_receta=bool(getattr(r, "existe_receta", False)),
                existe_archivo=bool(getattr(r, "existe_archivo", False)),

                importe_reconocido=float(getattr(r, "importe_reconocido", 0) or 0),
                importe_oficial=float(getattr(r, "importe_oficial", 0) or 0),

                estado_receta_id=int(getattr(r, "estado_receta_id", 0) or 0),
                estado_receta=str(getattr(r, "estado_receta", "") or ""),

                flag_debitos=bool(getattr(r, "flag_debitos", False)),

                frente_jpg=str(getattr(r, "frente_jpg", "") or ""),
            )

            mapped.append(vm)

        return mapped

    def _render_row(self, i: int, r: AuditoriaRowVM):

        ref = r.numero_referencia
        lote = r.nro_lote

        if r.es_revision:
            ref = "-"
            lote = "-"

        self._set_item(i, self.COL_RECETA, r.numero_receta)
        self._set_item(i, self.COL_REF, ref)
        self._set_item(i, self.COL_LOTE, lote)

        self._set_item(i, self.COL_RECETA_OK, "Sí" if r.existe_receta else "No", align=Qt.AlignCenter)
        self._set_item(i, self.COL_ARCHIVO_OK, "Sí" if r.existe_archivo else "No", align=Qt.AlignCenter)

        self._set_item(i, self.COL_RECON, f"{r.importe_reconocido:.2f}", align=Qt.AlignRight)
        self._set_item(i, self.COL_OFI, f"{r.importe_oficial:.2f}", align=Qt.AlignRight)

        self._set_item(i, self.COL_ESTADO, r.estado_receta)

        deb = "Sí" if (r.auditada and r.flag_debitos) else ("No" if r.auditada else "-")
        self._set_item(i, self.COL_DEBITOS, deb, align=Qt.AlignCenter)

        self._apply_row_colors(i, r)

        self._store_row_data(i, r)

        nombre_archivo = Path(r.frente_jpg).name if r.frente_jpg else ""
        self._set_item(i, self.COL_ARCHIVOS, nombre_archivo)

    def _store_row_data(self, row, r: AuditoriaRowVM):

        it = self.tbl.item(row, self.COL_RECETA)

        if not it:
            return

        data = {
            "asociacion_id": r.asociacion_id,
            "receta_id": r.receta_id,
            "frente": r.frente_jpg,
            "estado_id": r.estado_receta_id,
            "es_revision": r.es_revision,
        }

        it.setData(Qt.UserRole, data)

    def _apply_row_colors(self, row, r: AuditoriaRowVM):

        if r.auditada:
            color = QColor(252, 209, 22) if r.flag_debitos else Qt.green
            self._set_bg(row, self.COL_DEBITOS, color)

        self._set_bg(row, self.COL_OFI, Qt.green)

        if r.diferencia_montos:
            self._set_bg(row, self.COL_RECON, Qt.red)
        else:
            self._set_bg(row, self.COL_RECON, Qt.green)

    def _reload_auditoria(self):

        if not self._recepcion_id:
            return

        self.run_job(
            self._uc.load_auditoria,
            recepcion_id=self._recepcion_id,
            title="Actualizando auditoría...",
            on_result=self._apply_auditoria_rows,
            on_error=self._ui_error,
        )

    def _open_reasociar_receta(self, receta_id: int):

        dlg = ReasociarRecetaDialog(
            recepcion_id=self._recepcion_id,
            receta_id=receta_id,
            parent=self,
        )

        if dlg.exec():
            self._reload_auditoria()
