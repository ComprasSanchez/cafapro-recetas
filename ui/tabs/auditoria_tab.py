from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QComboBox, QCheckBox, QMenu, QApplication
)

from app.db.session import session_scope
from app.service.recetas.recetas_service import RecetaService
from ui.dialogs.forzar_asocaicion_dialog import ForzarAsociacionDialog
from ui.dialogs.numero_receta_dialog import NumeroRecetaDialog
from ui.tabs.base_tab import BaseTabWidget
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.auditoria_visual_dialog import AuditoriaVisualDialog

from ui.usecase.auditoria_usecase import (
    AuditoriaUseCase, RecepcionOut, EstadosOut, AuditoriaRowsOut, PreviewBytesOut
)


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
        dlg = RecepcionPickDialog(self, all=False)
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
        self.tbl.setHorizontalHeaderLabels([
            "Receta", "Referencia", "Lote",
            "Receta OK", "Archivo OK",
            "Reconocido", "Oficial", "Estado",
            "Débitos", "Archivo"
        ])

        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.tbl.verticalHeader().setMinimumSectionSize(self.ROW_H)
        self.tbl.setWordWrap(False)

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

        self.tbl.itemClicked.connect(self._on_item_clicked)
        self.tbl.itemSelectionChanged.connect(self._on_selection_changed)

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

        receta_item = self.tbl.item(row, self.COL_RECETA)
        ref_item = self.tbl.item(row, self.COL_REF)

        receta = receta_item.text() if receta_item else ""
        referencia = ref_item.text() if ref_item else ""

        receta_id = receta_item.data(Qt.ItemDataRole.UserRole + 3) if receta_item else None
        estado_id = receta_item.data(Qt.ItemDataRole.UserRole + 4) if receta_item else None

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
        self._rows_view = out.rows
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
                # 🔥 filtrar filas sin asociación
                idxs = [
                    i for i in idxs
                    if getattr(base_rows[i], "asociacion_id", None) is None
                ]

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

    def _render_table(self, rows: list) -> None:
        self._rendering_table = True
        self.tbl.setUpdatesEnabled(False)
        try:
            self.tbl.setSortingEnabled(False)
            self.tbl.setRowCount(len(rows))

            for i, r in enumerate(rows):
                asociacion_id = getattr(r, "asociacion_id", None)

                numero_receta = getattr(r, "numero_receta", "") or ""
                numero_referencia = getattr(r, "numero_referencia", "") or ""
                nro_lote = getattr(r, "nro_lote", "") or ""


                existe_archivo = bool(getattr(r, "existe_archivo", False))
                existe_receta = bool(getattr(r, "existe_receta", False))
                es_revision = (not existe_archivo) and existe_receta

                if es_revision:
                    numero_referencia = "-"
                    nro_lote = "-"

                importe_reconocido = float(getattr(r, "importe_reconocido", 0) or 0)
                importe_oficial = float(getattr(r, "importe_oficial", 0) or 0)

                estado_receta_id = self._estado_id(r)
                estado_receta = getattr(r, "estado_receta", "") or ""
                frente_jpg = (getattr(r, "frente_jpg", "") or "").strip()

                flag_debitos = bool(getattr(r, "flag_debitos", False))
                auditada = (estado_receta_id == 1) or es_revision

                self._set_item(i, self.COL_RECETA, str(numero_receta))
                if es_revision:
                    self._set_bg(i, self.COL_RECETA, QColor(210, 230, 255))
                self._set_item(i, self.COL_REF, str(numero_referencia))
                self._set_item(i, self.COL_LOTE, str(nro_lote))
                self._set_item(i, self.COL_RECETA_OK, "SI" if existe_receta else "NO", align=Qt.AlignCenter)
                self._set_item(i, self.COL_ARCHIVO_OK, "SI" if existe_archivo else "NO", align=Qt.AlignCenter)
                self._set_item(i, self.COL_RECON, f"{importe_reconocido:.2f}", align=Qt.AlignRight)
                self._set_item(i, self.COL_OFI, f"{importe_oficial:.2f}", align=Qt.AlignRight)
                self._set_item(i, self.COL_ESTADO, str(estado_receta))
                self._set_item(
                    i,
                    self.COL_DEBITOS,
                    "SI" if (auditada and flag_debitos) else ("NO" if auditada else "-"),
                    align=Qt.AlignCenter
                )

                c0 = self.tbl.item(i, self.COL_RECETA)

                if c0:
                    c0.setData(Qt.ItemDataRole.UserRole, asociacion_id)
                    c0.setData(Qt.ItemDataRole.UserRole + 1, frente_jpg)
                    c0.setData(Qt.ItemDataRole.UserRole + 2, es_revision)
                    c0.setData(Qt.ItemDataRole.UserRole + 3, getattr(r, "receta_id", None))
                    c0.setData(Qt.ItemDataRole.UserRole + 4, getattr(r, "estado_receta_id", None))

                if auditada:
                    color = QColor(252, 209, 22) if flag_debitos else Qt.GlobalColor.green
                    self._set_bg(i, self.COL_DEBITOS, color)

                self._set_bg(i, self.COL_OFI, Qt.GlobalColor.green)

                if self._is_diff_money(importe_reconocido, importe_oficial):
                    self._set_bg(i, self.COL_RECON, Qt.GlobalColor.red)
                else:
                    self._set_bg(i, self.COL_RECON, Qt.GlobalColor.green)

                frente_path = (getattr(r, "frente_jpg", "") or "").strip()
                nombre_archivo = Path(frente_path).name if frente_path else ""

                self._set_item(i, self.COL_ARCHIVOS, nombre_archivo)

            self.tbl.setSortingEnabled(True)
            self.tbl.clearSelection()
            self.tbl.setCurrentCell(-1, -1)
            self._clear_preview()

        finally:
            self.tbl.setUpdatesEnabled(True)
            self._rendering_table = False

    def _set_item(self, row: int, col: int, text: str, align: Qt.AlignmentFlag | None = None) -> None:
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignVCenter | (align if align is not None else Qt.AlignLeft))
        self.tbl.setItem(row, col, it)

    # -------------------------
    # Selection -> Preview
    # -------------------------
    def _on_selection_changed(self) -> None:
        if self._rendering_table:
            return

        self._sync_visual_button_state()

        it = self.tbl.currentItem()
        if not it:
            self._clear_preview()
            return

        self._on_item_clicked(it)

    # -------------------------
    # Preview async
    # -------------------------
    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        c0 = self.tbl.item(row, self.COL_RECETA)
        if not c0:
            return

        raw = (c0.data(Qt.ItemDataRole.UserRole + 1) or "").strip()
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
        it = self.tbl.currentItem()
        if not it:
            self.btn_visual.setEnabled(False)
            return
        row = it.row()
        c0 = self.tbl.item(row, self.COL_RECETA)
        if not c0:
            self.btn_visual.setEnabled(False)
            return
        asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
        self.btn_visual.setEnabled(bool(asociacion_id))

    def _on_open_auditoria_visual(self) -> None:
        start_row = self.tbl.currentRow()
        if start_row < 0:
            return

        # construir lista desde la fila actual hasta el final
        asociacion_ids: list[int] = []
        for row in range(start_row, self.tbl.rowCount()):
            c0 = self.tbl.item(row, self.COL_RECETA)
            if not c0:
                continue
            asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
            if asociacion_id:
                asociacion_ids.append(int(asociacion_id))

        if not asociacion_ids:
            QMessageBox.warning(self, "Sin registros", "No hay asociaciones para auditar desde esta fila.")
            return

        dlg = AuditoriaVisualDialog(
            asociacion_ids=asociacion_ids,
            start_index=0,
            parent=self,
            creado_por_usuario_id=self.creado_por_usuario_id,
        )
        dlg.exec()

        # refresca UNA sola vez
        if self._recepcion_id:
            self.run_job(
                self._uc.load_auditoria,
                recepcion_id=self._recepcion_id,
                title="Actualizando auditoría…",
                on_result=self._apply_auditoria_rows,
                on_error=self._ui_error,
            )

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
            QMessageBox.warning(self, "Atención", "Debe ingresar un número de receta.")
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

        self._after_anular_receta()

    def _after_anular_receta(self):

        if not self._recepcion_id:
            return

        self.run_job(
            self._uc.load_auditoria,
            recepcion_id=self._recepcion_id,
            title="Actualizando auditoría...",
            on_result=self._apply_auditoria_rows,
            on_error=self._ui_error,
        )

    def _duplicar_receta(self, receta_id: int):

        row = self.tbl.currentRow()

        dlg = NumeroRecetaDialog(self)

        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        nro_receta = dlg.numero_receta()

        if not nro_receta:
            QMessageBox.warning(self, "Atención", "Debe ingresar un número de receta.")
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

        self._after_anular_receta()