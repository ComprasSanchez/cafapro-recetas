from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QEvent, QThreadPool, QTimer
from PySide6.QtGui import QPixmap, QColor, QPen, QIcon
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QComboBox, QCheckBox, QMenu, QApplication, QStyle,
    QStyledItemDelegate,
)

from ui.dialogs.forzar_asociacion_dialog import ForzarAsociacionDialog
from ui.dialogs.numero_receta_dialog import NumeroRecetaDialog
from ui.dialogs.reasociar_receta_dialog import ReasociarRecetaDialog
from ui.dialogs.historial_search_dialog import HistorialSearchDialog
from ui.models.auditoria_row_vm import AuditoriaRowVM
from ui.tabs.base_tab import BaseTabWidget
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.auditoria_visual_dialog import AuditoriaVisualDialog
from ui.jobs.jobs_service import ServiceJob
from ui.security.permissions import is_admin

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


class SortableTableWidgetItem(QTableWidgetItem):
    SORT_ROLE = Qt.ItemDataRole.UserRole + 50

    def __lt__(self, other) -> bool:
        if isinstance(other, QTableWidgetItem):
            left = self.data(self.SORT_ROLE)
            right = other.data(self.SORT_ROLE)
            if left is not None and right is not None:
                try:
                    return float(left) < float(right)
                except Exception:
                    pass
        return super().__lt__(other)


class AuditoriaTab(BaseTabWidget):
    ROW_H = 32  # un toque más compacta
    ESTADO_RECETA_REVISION_ID = 3

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
    COL_ELIMINAR = 10

    def __init__(self, parent=None, creado_por_usuario_id: int | None = None, current_user=None):
        super().__init__(parent)
        self.footer_channel = "auditoria"
        self.creado_por_usuario_id = creado_por_usuario_id
        self.current_user = current_user
        self._is_admin = is_admin(current_user)

        self._recepcion_id: int | None = None
        self._rows_view: list = []
        self._last_preview_path: str | None = None
        self._active_row: int = -1
        self._active_marker_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
        self._empty_icon = QIcon()

        self._uc = AuditoriaUseCase()
        self._auditoria_loading = False
        self._preview_runner = QThreadPool(self)
        self._preview_runner.setMaxThreadCount(1)
        self._active_preview_jobs: set[ServiceJob] = set()
        self._preview_request_id = 0
        self.btn_delete_revisiones: QPushButton | None = None
        self.btn_mark_revisiones: QPushButton | None = None
        self.btn_clear_revisiones: QPushButton | None = None
        self._marked_revision_ids: set[int] = set()

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
            job_key="auditoria:estados",
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
        self.btn_reload.setEnabled(False)

        self.btn_buscar_receta = QPushButton("Buscar receta")
        self.btn_buscar_receta.setMinimumHeight(32)
        self.btn_buscar_receta.clicked.connect(self._on_open_historial_search)

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
        row0_l.addWidget(self.btn_buscar_receta, 0)

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
            job_key="auditoria:load_recepcion",
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
        self._marked_revision_ids.clear()
        self._clear_table_and_preview()
        self._update_reload_button_state()
        self._refresh_admin_actions_state()
        self._request_reload_auditoria(title="Cargando auditoría…")

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

        self.tbl = QTableWidget(0, 11)
        self.tbl.setObjectName("auditoria_rows_table")
        self.tbl.setHorizontalHeaderLabels([
            "Receta", "Referencia", "Lote",
            "Receta OK", "Archivo OK",
            "Reconocido", "Oficial", "Estado",
            "Débitos", "Archivo", "Eliminar"
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
        hh.resizeSection(self.COL_ELIMINAR, 85)

        hh.setContextMenuPolicy(Qt.CustomContextMenu)
        hh.customContextMenuRequested.connect(self._show_column_menu)

        self.tbl.cellClicked.connect(self._on_cell_clicked)
        self.tbl.currentCellChanged.connect(self._on_current_cell_changed)
        self.tbl.itemChanged.connect(self._on_table_item_changed)

        if not self._is_admin:
            self.tbl.setColumnHidden(self.COL_ELIMINAR, True)

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

        self.lb_preview_delete = QLabel("")
        self.lb_preview_delete.setVisible(False)
        self.lb_preview_delete.setObjectName("muted")
        rp_l.addWidget(self.lb_preview_delete, 0)

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

        if self._is_admin:
            self.btn_mark_revisiones = QPushButton("Marcar revisiones")
            self.btn_mark_revisiones.setMinimumHeight(28)
            self.btn_mark_revisiones.clicked.connect(self._on_mark_revisiones)
            l.addWidget(self.btn_mark_revisiones, 0)

            self.btn_clear_revisiones = QPushButton("Limpiar selección")
            self.btn_clear_revisiones.setMinimumHeight(28)
            self.btn_clear_revisiones.clicked.connect(self._on_clear_revisiones)
            l.addWidget(self.btn_clear_revisiones, 0)

            self.btn_delete_revisiones = QPushButton("Eliminar revisiones")
            self.btn_delete_revisiones.setProperty("danger", True)
            self.btn_delete_revisiones.setMinimumHeight(28)
            self.btn_delete_revisiones.clicked.connect(self._on_delete_revisiones)
            l.addWidget(self.btn_delete_revisiones, 0)

        l.addStretch(1)
        return bar

    def _show_column_menu(self, pos):
        menu = QMenu(self)

        for col in range(self.tbl.columnCount()):
            if (not self._is_admin) and col == self.COL_ELIMINAR:
                continue

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

            if self._is_admin:
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
        self._refresh_admin_actions_state()

    def _apply_auditoria_rows(self, out: AuditoriaRowsOut) -> None:
        self._rows_view = self._map_rows(out.rows)
        self.lb_status.setText(f"Auditoría cargada: {len(self._rows_view)} registros")
        self._apply_filters()

    def _update_reload_button_state(self) -> None:
        if not hasattr(self, "btn_reload"):
            return
        self.btn_reload.setEnabled(bool(self._recepcion_id) and not self._auditoria_loading)

    def _request_reload_auditoria(self, *, title: str) -> None:
        if not self._recepcion_id:
            return

        self._marked_revision_ids.clear()
        self._sync_preview_delete_marker()
        self._refresh_admin_actions_state()

        if self._auditoria_loading:
            self.footer_set(info="La auditoría ya se está actualizando.")
            return

        self._auditoria_loading = True
        self._update_reload_button_state()

        recepcion_id = int(self._recepcion_id)

        self.run_job(
            self._uc.load_auditoria,
            recepcion_id=recepcion_id,
            title=title,
            on_result=lambda out, rid=recepcion_id: self._on_reload_result(rid, out),
            on_error=lambda err, rid=recepcion_id: self._on_reload_error(rid, err),
            on_finished=self._on_reload_finished,
            job_key="auditoria:reload",
        )

    def _on_reload_result(self, recepcion_id: int, out: AuditoriaRowsOut) -> None:
        if int(self._recepcion_id or 0) != int(recepcion_id):
            return
        self._apply_auditoria_rows(out)

    def _on_reload_error(self, recepcion_id: int, err_text: str) -> None:
        if int(self._recepcion_id or 0) != int(recepcion_id):
            return
        self._ui_error(err_text)

    def _on_reload_finished(self) -> None:
        self._auditoria_loading = False
        self._update_reload_button_state()
        self._refresh_admin_actions_state()

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
        self._refresh_admin_actions_state()

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

    def _set_item_sortable(
        self,
        row: int,
        col: int,
        text: str,
        *,
        sort_value: float,
        align: Qt.AlignmentFlag | None = None,
    ) -> None:
        it = SortableTableWidgetItem(text)
        it.setData(SortableTableWidgetItem.SORT_ROLE, float(sort_value))
        it.setTextAlignment(Qt.AlignVCenter | (align if align is not None else Qt.AlignLeft))
        it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable & ~Qt.ItemFlag.ItemIsSelectable)
        self.tbl.setItem(row, col, it)

    @staticmethod
    def _lote_sort_value(raw_lote: str) -> float:
        value = str(raw_lote or "").strip()
        if not value or value == "-":
            return 1e15
        try:
            return float(int(value))
        except Exception:
            return 1e15

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
        self._sync_preview_delete_marker()

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

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if self._rendering_table or not self._is_admin:
            return

        if item.column() != self.COL_ELIMINAR:
            return

        c0 = self.tbl.item(item.row(), self.COL_RECETA)
        if not c0:
            return

        data = c0.data(Qt.UserRole) or {}
        receta_id = int(data.get("receta_id", 0) or 0)
        estado_id = int(data.get("estado_id", 0) or 0)

        if receta_id <= 0 or estado_id != self.ESTADO_RECETA_REVISION_ID:
            return

        if item.checkState() == Qt.CheckState.Checked:
            self._marked_revision_ids.add(receta_id)
        else:
            self._marked_revision_ids.discard(receta_id)

        self._sync_preview_delete_marker()
        self._refresh_admin_actions_state()

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
            self._sync_preview_delete_marker()
            return

        src = self._uc.resolve_preview_src(raw)

        self._last_preview_path = src

        self._load_preview_async(src)

        self._sync_visual_button_state()
        self._sync_preview_delete_marker()

    def _load_preview_async(self, path: str) -> None:
        vw = max(200, self.scroll.viewport().width() - 12)
        vh = max(200, self.scroll.viewport().height() - 12)
        self._preview_request_id += 1
        req_id = self._preview_request_id

        self.img_preview.setText("Cargando…")
        self.img_preview.setPixmap(QPixmap())

        job = ServiceJob(
            self._uc.load_preview_bytes,
            path=path,
            vw=vw,
            vh=vh,
            title="Cargando imagen…",
        )
        self._active_preview_jobs.add(job)

        def _cleanup() -> None:
            self._active_preview_jobs.discard(job)

        job.signals.result.connect(lambda out, rid=req_id: self._on_preview_result(rid, out))
        job.signals.error.connect(lambda err, rid=req_id: self._on_preview_error(rid, err))
        job.signals.finished.connect(lambda _msg: _cleanup())

        self._preview_runner.start(job)

    def _on_preview_result(self, req_id: int, out: PreviewBytesOut) -> None:
        if req_id != self._preview_request_id:
            return
        self._apply_preview_bytes(out)

    def _on_preview_error(self, req_id: int, err_text: str) -> None:
        if req_id != self._preview_request_id:
            return
        self._ui_error_preview(err_text)

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
        self._preview_request_id += 1
        self.img_preview.setPixmap(QPixmap())
        self.img_preview.setText("Sin imagen")
        self.lb_preview_delete.setVisible(False)
        self.lb_preview_delete.setText("")
        self._last_preview_path = None
        self.btn_visual.setEnabled(False)

    def _sync_preview_delete_marker(self) -> None:
        if not self._is_admin:
            self.lb_preview_delete.setVisible(False)
            self.lb_preview_delete.setText("")
            return

        row = self._active_row if self._active_row >= 0 else self.tbl.currentRow()
        if row < 0:
            self.lb_preview_delete.setVisible(False)
            self.lb_preview_delete.setText("")
            return

        it = self.tbl.item(row, self.COL_ELIMINAR)
        if not it or it.checkState() != Qt.CheckState.Checked:
            self.lb_preview_delete.setVisible(False)
            self.lb_preview_delete.setText("")
            return

        self.lb_preview_delete.setText("Marcada para eliminar")
        self.lb_preview_delete.setVisible(True)

    def _clear_table_and_preview(self) -> None:
        self.tbl.setRowCount(0)
        self.lb_status.setText("Cargando auditoría…")
        self.lb_filtered.setText("")
        self._clear_preview()
        self._refresh_admin_actions_state()

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
            current_user=self.current_user,
        )

        dlg.exec()
        self._reload_auditoria()

    def _on_open_historial_search(self) -> None:
        dlg = HistorialSearchDialog(parent=self)
        dlg.exec()

    def _refresh_admin_actions_state(self) -> None:
        if not self._is_admin or not self.btn_delete_revisiones:
            return

        has_recepcion = bool(self._recepcion_id)
        has_marked = bool(self._collect_marked_revision_receta_ids())
        has_visible_revisiones = bool(self._collect_visible_revision_receta_ids())

        can_delete = (
            has_recepcion
            and not self._auditoria_loading
            and self._is_estado_revision_selected()
            and has_marked
        )
        self.btn_delete_revisiones.setEnabled(can_delete)

        if self.btn_mark_revisiones:
            self.btn_mark_revisiones.setEnabled(
                has_recepcion
                and not self._auditoria_loading
                and self._is_estado_revision_selected()
                and has_visible_revisiones
            )

        if self.btn_clear_revisiones:
            self.btn_clear_revisiones.setEnabled(
                has_recepcion
                and not self._auditoria_loading
                and has_marked
            )

    def _is_estado_revision_selected(self) -> bool:
        if not hasattr(self, "cb_estado"):
            return False
        data = self.cb_estado.currentData()
        if data is None or data == "SIN_ASOC":
            return False
        try:
            return int(data) == self.ESTADO_RECETA_REVISION_ID
        except Exception:
            return False

    def _collect_visible_revision_receta_ids(self) -> list[int]:
        ids: list[int] = []
        seen: set[int] = set()

        for row in range(self.tbl.rowCount()):
            c0 = self.tbl.item(row, self.COL_RECETA)
            if not c0:
                continue

            data = c0.data(Qt.UserRole) or {}
            estado_id = int(data.get("estado_id", 0) or 0)
            receta_id = int(data.get("receta_id", 0) or 0)

            if estado_id != self.ESTADO_RECETA_REVISION_ID or receta_id <= 0:
                continue
            if receta_id in seen:
                continue

            seen.add(receta_id)
            ids.append(receta_id)

        return ids

    def _collect_marked_revision_receta_ids(self) -> list[int]:
        ids: list[int] = []
        seen: set[int] = set()

        for row in range(self.tbl.rowCount()):
            mark_it = self.tbl.item(row, self.COL_ELIMINAR)
            if not mark_it or mark_it.checkState() != Qt.CheckState.Checked:
                continue

            c0 = self.tbl.item(row, self.COL_RECETA)
            if not c0:
                continue

            data = c0.data(Qt.UserRole) or {}
            estado_id = int(data.get("estado_id", 0) or 0)
            receta_id = int(data.get("receta_id", 0) or 0)

            if estado_id != self.ESTADO_RECETA_REVISION_ID or receta_id <= 0:
                continue
            if receta_id in seen:
                continue

            seen.add(receta_id)
            ids.append(receta_id)

        return ids

    def _set_mark_for_visible_revisiones(self, *, checked: bool) -> None:
        self.tbl.blockSignals(True)
        try:
            for row in range(self.tbl.rowCount()):
                c0 = self.tbl.item(row, self.COL_RECETA)
                mark_it = self.tbl.item(row, self.COL_ELIMINAR)
                if not c0 or not mark_it:
                    continue

                data = c0.data(Qt.UserRole) or {}
                estado_id = int(data.get("estado_id", 0) or 0)
                receta_id = int(data.get("receta_id", 0) or 0)

                if estado_id != self.ESTADO_RECETA_REVISION_ID or receta_id <= 0:
                    continue

                mark_it.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

                if checked:
                    self._marked_revision_ids.add(receta_id)
                else:
                    self._marked_revision_ids.discard(receta_id)
        finally:
            self.tbl.blockSignals(False)

        self._sync_preview_delete_marker()
        self._refresh_admin_actions_state()

    def _on_mark_revisiones(self) -> None:
        if not self._is_admin:
            return
        self._set_mark_for_visible_revisiones(checked=True)

    def _on_clear_revisiones(self) -> None:
        if not self._is_admin:
            return
        self._marked_revision_ids.clear()
        self._set_mark_for_visible_revisiones(checked=False)

    def _on_delete_revisiones(self) -> None:
        if not self._is_admin:
            return

        receta_ids = self._collect_marked_revision_receta_ids()
        if not receta_ids:
            QMessageBox.information(self, "Sin datos", "No hay recetas marcadas para eliminar.")
            return

        ans = QMessageBox.warning(
            self,
            "Eliminar revisiones",
            (
                f"Se eliminarán {len(receta_ids)} recetas en revisión.\n\n"
                "También se eliminarán imágenes y datos asociados.\n"
                "Esta acción no se puede deshacer."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return

        self.run_job(
            self._uc.eliminar_sobrantes_bulk,
            receta_ids=receta_ids,
            title="Eliminando recetas en revisión...",
            on_result=self._on_delete_revisiones_done,
            on_error=self._ui_error,
            job_key=f"auditoria:eliminar_bulk:{int(self._recepcion_id or 0)}",
        )

    def _on_delete_revisiones_done(self, out: dict) -> None:
        total = int(out.get("total", 0) or 0)
        eliminadas = int(out.get("eliminadas", 0) or 0)
        omitidas = int(out.get("omitidas", 0) or 0)
        errores = list(out.get("errores") or [])

        msg = [
            f"Total evaluadas: {total}",
            f"Eliminadas: {eliminadas}",
            f"Omitidas: {omitidas}",
        ]
        if errores:
            msg.append(f"Errores: {len(errores)}")

        QMessageBox.information(self, "Eliminación masiva completada", "\n".join(msg))
        self._marked_revision_ids.clear()
        self._sync_preview_delete_marker()
        self._refresh_admin_actions_state()
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
            self._request_reload_auditoria(title="Actualizando auditoría...")

    def _anular_receta(self, receta_id: int):
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

        self.run_job(
            self._uc.anular_receta,
            receta_id=receta_id,
            nro_receta=nro_receta,
            title="Anulando receta...",
            on_result=lambda _out: self._reload_auditoria(),
            job_key=f"auditoria:anular:{int(receta_id)}",
        )

    def _duplicar_receta(self, receta_id: int):
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

        self.run_job(
            self._uc.duplicar_receta,
            receta_id=receta_id,
            nro_receta=nro_receta,
            title="Marcando receta duplicada...",
            on_result=lambda _out: self._reload_auditoria(),
            job_key=f"auditoria:duplicar:{int(receta_id)}",
        )

    def _eliminar_sobrante(self, receta_id: int):
        if not self._is_admin:
            return

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

        self.run_job(
            self._uc.eliminar_sobrante,
            receta_id=receta_id,
            title="Eliminando receta...",
            on_result=lambda _out, rid=receta_id: self._on_delete_single_done(int(rid)),
            job_key=f"auditoria:eliminar:{int(receta_id)}",
        )

    def _on_delete_single_done(self, receta_id: int) -> None:
        self._marked_revision_ids.discard(int(receta_id))
        self._sync_preview_delete_marker()
        self._refresh_admin_actions_state()
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

        self.run_job(
            self._uc.desasociar_receta,
            receta_id=receta_id,
            title="Desasociando receta...",
            on_result=lambda _out: self._reload_auditoria(),
            job_key=f"auditoria:desasociar:{int(receta_id)}",
        )

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
        self._set_item_sortable(
            i,
            self.COL_LOTE,
            lote,
            sort_value=self._lote_sort_value(lote),
            align=Qt.AlignCenter,
        )

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

        self._set_delete_marker_item(i, r)

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

    def _set_delete_marker_item(self, row: int, r: AuditoriaRowVM) -> None:
        it = QTableWidgetItem("")
        it.setTextAlignment(Qt.AlignCenter)

        if self._is_admin and r.es_revision and int(r.receta_id or 0) > 0:
            flags = it.flags()
            flags |= Qt.ItemFlag.ItemIsUserCheckable
            flags |= Qt.ItemFlag.ItemIsEnabled
            flags &= ~Qt.ItemFlag.ItemIsEditable
            flags &= ~Qt.ItemFlag.ItemIsSelectable
            it.setFlags(flags)

            rid = int(r.receta_id)
            it.setCheckState(
                Qt.CheckState.Checked if rid in self._marked_revision_ids else Qt.CheckState.Unchecked
            )
        else:
            it.setText("-")
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable & ~Qt.ItemFlag.ItemIsSelectable)

        self.tbl.setItem(row, self.COL_ELIMINAR, it)

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
        self._request_reload_auditoria(title="Actualizando auditoría...")

    def _open_reasociar_receta(self, receta_id: int):

        dlg = ReasociarRecetaDialog(
            recepcion_id=self._recepcion_id,
            receta_id=receta_id,
            parent=self,
        )

        if dlg.exec():
            self._reload_auditoria()
