from __future__ import annotations

from pathlib import Path
from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter, QScrollArea,
    QComboBox, QCheckBox
)

from app.db.session import session_scope
from app.service.recepcion_service import RecepcionService
from app.service.view_auditoria import ViewAuditoriaService
from app.service.estado_receta_service import EstadoRecetaService
from ui.dialogs.recepcion_pick_dialog import RecepcionPickDialog
from ui.dialogs.auditoria_visual_dialog import AuditoriaVisualDialog


class AuditoriaTab(QWidget):
    ROW_H = 34

    def __init__(self, parent=None, creado_por_usuario_id: int | None = None):
        super().__init__(parent)
        self.creado_por_usuario_id = creado_por_usuario_id

        self._recepcion_id: int | None = None
        self._rows_view = []          # cache rows de la view (base)
        self._rows_search = []        # cache tuples lower() para buscar
        self._last_preview_path: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._build_header(), 0)
        root.addWidget(self._build_body(), 1)

        self._load_estado_receta_combo()

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._apply_filters)

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
        row1_l.addWidget(self.in_obs, 0)         # valor obs
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
        dlg = RecepcionPickDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        rid = dlg.selected_recepcion_id()
        if rid:
            self._load_recepcion(rid)

    # -------------------------
    # BODY (status + filtros + split)
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

        # -------- IZQUIERDA: TABLA --------
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.setSpacing(0)

        self.tbl = QTableWidget(0, 8)
        self.tbl.setHorizontalHeaderLabels([
            "Receta", "Referencia", "Lote",
            "Receta OK", "Archivo OK",
            "Reconocido", "Oficial", "Estado",
        ])
        self.tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tbl.setAlternatingRowColors(True)
        self.tbl.setSortingEnabled(True)
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)
        self.tbl.verticalHeader().setMinimumSectionSize(self.ROW_H)

        hh = self.tbl.horizontalHeader()
        hh.setStretchLastSection(True)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        hh.setHighlightSections(False)

        self.tbl.itemClicked.connect(self._on_item_clicked)
        self.tbl.itemSelectionChanged.connect(self._sync_visual_button_state)

        left_l.addWidget(self.tbl, 1)
        split.addWidget(left)

        # -------- DERECHA: PREVIEW --------
        right = QFrame()
        right.setObjectName("panel")  # si no existe en QSS, igual no rompe
        rp_l = QVBoxLayout(right)
        rp_l.setContentsMargins(8, 8, 8, 8)
        rp_l.setSpacing(8)

        title = QLabel("Vista previa")
        title.setProperty("role", "subtitle")
        rp_l.addWidget(title, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.img_preview = QLabel("Sin imagen")
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_preview.setScaledContents(False)

        self.scroll.setWidget(self.img_preview)
        rp_l.addWidget(self.scroll, 1)

        right.setFixedWidth(480)
        split.addWidget(right)

        split.setStretchFactor(0, 5)
        split.setStretchFactor(1, 2)

        return body

    def _build_filters(self) -> QFrame:
        bar = QFrame()
        l = QHBoxLayout(bar)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)

        l.addWidget(QLabel("Estado:"))
        self.cb_estado = QComboBox()
        self.cb_estado.setMinimumHeight(28)
        self.cb_estado.setMinimumWidth(220)
        self.cb_estado.addItem("Todos", None)
        self.cb_estado.currentIndexChanged.connect(self._apply_filters)
        l.addWidget(self.cb_estado, 0)

        self.chk_diff_montos = QCheckBox("Solo diferencias $")
        self.chk_diff_montos.toggled.connect(self._apply_filters)
        l.addWidget(self.chk_diff_montos, 0)

        l.addWidget(QLabel("Buscar:"))
        self.in_search = QLineEdit()
        self.in_search.setMinimumHeight(28)
        self.in_search.setPlaceholderText("Receta / Referencia / Lote…")
        self.in_search.setClearButtonEnabled(True)
        self.in_search.setMaximumWidth(320)
        self.in_search.textChanged.connect(self._on_search_changed)
        l.addWidget(self.in_search, 0)

        self.lb_filtered = QLabel("")
        self.lb_filtered.setObjectName("muted")
        l.addWidget(self.lb_filtered, 0)

        l.addStretch(1)
        return bar

    # -------------------------
    # data + render
    # -------------------------
    def _refresh_auditoria_table(self) -> None:
        if not self._recepcion_id:
            self.tbl.setRowCount(0)
            self.lb_status.setText("Seleccioná una recepción para cargar la auditoría.")
            self.lb_filtered.setText("")
            self.btn_visual.setEnabled(False)
            return

        try:
            with session_scope() as s:
                self._rows_view = list(ViewAuditoriaService.list(s, self._recepcion_id))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la auditoría:\n{e}")
            return

        self._rows_search = [
            (
                str(getattr(r, "numero_receta", "") or "").lower(),
                str(getattr(r, "numero_referencia", "") or "").lower(),
                str(getattr(r, "nro_lote", "") or "").lower(),
            )
            for r in self._rows_view
        ]

        self.lb_status.setText(f"Auditoría cargada: {len(self._rows_view)} registros")
        self._apply_filters()

    def _apply_filters(self) -> None:
        base_rows = self._rows_view or []
        total = len(base_rows)

        estado_id = self.cb_estado.currentData() if hasattr(self, "cb_estado") else None
        only_diff = self.chk_diff_montos.isChecked() if hasattr(self, "chk_diff_montos") else False
        q = (self.in_search.text() or "").strip().lower() if hasattr(self, "in_search") else ""

        idxs = list(range(total))

        # 1) Estado
        if estado_id is not None:
            eid = int(estado_id)
            idxs = [
                i for i in idxs
                if int(getattr(base_rows[i], "estado_receta_id", 0) or 0) == eid
            ]

        # 2) Diferencias
        if only_diff:
            def is_diff(i: int) -> bool:
                r = base_rows[i]
                rec = float(getattr(r, "importe_reconocido", 0) or 0)
                ofi = float(getattr(r, "importe_oficial", 0) or 0)
                return abs(rec - ofi) > 0.009

            idxs = [i for i in idxs if is_diff(i)]

        # 3) Buscar (cache)
        if q:
            cache = self._rows_search if len(self._rows_search) == total else None
            if cache:
                idxs = [i for i in idxs if (q in cache[i][0] or q in cache[i][1] or q in cache[i][2])]
            else:
                idxs = [
                    i for i in idxs
                    if (
                        q in str(getattr(base_rows[i], "numero_receta", "") or "").lower()
                        or q in str(getattr(base_rows[i], "numero_referencia", "") or "").lower()
                        or q in str(getattr(base_rows[i], "nro_lote", "") or "").lower()
                    )
                ]

        rows = [base_rows[i] for i in idxs]
        self._render_table(rows)

        self.lb_filtered.setText(f"Mostrando {len(rows)} de {total}")

    def _render_table(self, rows: list) -> None:
        self.tbl.setSortingEnabled(False)
        self.tbl.setRowCount(len(rows))

        for i, r in enumerate(rows):
            asociacion_id = getattr(r, "asociacion_id", None)
            numero_receta = getattr(r, "numero_receta", "") or ""
            numero_referencia = getattr(r, "numero_referencia", "") or ""
            nro_lote = getattr(r, "nro_lote", "") or ""

            existe_archivo = bool(getattr(r, "existe_archivo", False))
            existe_receta = bool(getattr(r, "existe_receta", False))

            importe_reconocido = getattr(r, "importe_reconocido", 0) or 0
            importe_oficial = getattr(r, "importe_oficial", 0) or 0

            estado_receta = getattr(r, "estado_receta", "") or ""
            frente_jpg = (getattr(r, "frente_jpg", "") or "").strip()

            self._set_item(i, 0, str(numero_receta))
            self._set_item(i, 1, str(numero_referencia))
            self._set_item(i, 2, str(nro_lote))
            self._set_item(i, 3, "SI" if existe_receta else "NO", align=Qt.AlignCenter)
            self._set_item(i, 4, "SI" if existe_archivo else "NO", align=Qt.AlignCenter)
            self._set_item(i, 5, f"{float(importe_reconocido):.2f}", align=Qt.AlignRight)
            self._set_item(i, 6, f"{float(importe_oficial):.2f}", align=Qt.AlignRight)
            self._set_item(i, 7, str(estado_receta))

            # data en celda 0
            c0 = self.tbl.item(i, 0)
            c0.setData(Qt.ItemDataRole.UserRole, asociacion_id)
            c0.setData(Qt.ItemDataRole.UserRole + 1, frente_jpg)

        self.tbl.setSortingEnabled(True)

        if rows:
            QTimer.singleShot(0, self._select_first_row)
        else:
            self.img_preview.setPixmap(QPixmap())
            self.img_preview.setText("Sin imagen")
            self.btn_visual.setEnabled(False)

    def _set_item(self, row: int, col: int, text: str, align: Qt.AlignmentFlag | None = None) -> None:
        it = QTableWidgetItem(text)
        if align is None:
            it.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        else:
            it.setTextAlignment(Qt.AlignVCenter | align)
        self.tbl.setItem(row, col, it)

    def _select_first_row(self) -> None:
        if self.tbl.rowCount() == 0:
            return
        self.tbl.setFocus()
        self.tbl.setCurrentCell(0, 0)
        self.tbl.selectRow(0)

        it = self.tbl.item(0, 0)
        if it:
            self.tbl.scrollToItem(it, QAbstractItemView.ScrollHint.PositionAtTop)
            self._on_item_clicked(it)

    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        c0 = self.tbl.item(row, 0)
        if not c0:
            return

        asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
        frente_jpg = (c0.data(Qt.ItemDataRole.UserRole + 1) or "").strip()

        if frente_jpg:
            self._set_preview_from_file(frente_jpg)
        else:
            self.img_preview.setPixmap(QPixmap())
            self.img_preview.setText("Sin imagen")
            self._last_preview_path = None

        self.lb_status.setText(f"Seleccionado asociacion_id={asociacion_id}")
        self._sync_visual_button_state()

    # -------------------------
    # preview
    # -------------------------
    def _set_preview_from_file(self, path: str) -> None:
        try:
            p = Path(path)
            if not p.exists():
                raise FileNotFoundError(f"No existe: {p}")

            pil_img = Image.open(p).convert("RGB")

            vw = max(200, self.scroll.viewport().width() - 12)
            vh = max(200, self.scroll.viewport().height() - 12)

            scale = min(vw / pil_img.width, vh / pil_img.height)
            scale = max(scale, 0.30)

            new_w = int(pil_img.width * scale)
            new_h = int(pil_img.height * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            qimg = ImageQt(pil_img)
            pix = QPixmap.fromImage(qimg)

            self.img_preview.setPixmap(pix)
            self.img_preview.resize(pix.size())
            self.img_preview.setText("")
            self._last_preview_path = str(p)

        except Exception as e:
            self.img_preview.setPixmap(QPixmap())
            self.img_preview.setText(f"No se pudo cargar la imagen.\n{e}")
            self._last_preview_path = None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._last_preview_path:
            self._set_preview_from_file(self._last_preview_path)

    # -------------------------
    # recepción + estados
    # -------------------------
    def _load_recepcion(self, recepcion_id: int) -> None:
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
        self.in_numero.setText(str(rec.numero))
        self.in_prestador.setText(str(rec.prestador))
        self.in_obs.setText(str(rec.obra_social))

        periodo_txt = str(rec.periodo)
        self.in_periodo.setText(periodo_txt)

        quincena = "-"
        if "Q1" in periodo_txt:
            quincena = "1ª"
        elif "Q2" in periodo_txt:
            quincena = "2ª"
        self.in_quincena.setText(quincena)

        self._refresh_auditoria_table()

    def _sync_visual_button_state(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            self.btn_visual.setEnabled(False)
            return

        row = it.row()
        c0 = self.tbl.item(row, 0)
        if not c0:
            self.btn_visual.setEnabled(False)
            return

        asociacion_id = c0.data(Qt.ItemDataRole.UserRole)
        self.btn_visual.setEnabled(bool(asociacion_id))

    def _on_open_auditoria_visual(self) -> None:
        it = self.tbl.currentItem()
        if not it:
            return
        c0 = self.tbl.item(it.row(), 0)
        asociacion_id = c0.data(Qt.ItemDataRole.UserRole) if c0 else None
        if not asociacion_id:
            return

        dlg = AuditoriaVisualDialog(asociacion_id=int(asociacion_id), parent=self)
        dlg.exec()

    def _load_estado_receta_combo(self) -> None:
        if not hasattr(self, "cb_estado"):
            return

        try:
            with session_scope() as s:
                estados = EstadoRecetaService.list(s)
        except Exception:
            estados = []

        self.cb_estado.blockSignals(True)
        self.cb_estado.clear()
        self.cb_estado.addItem("Todos", None)

        for e in estados:
            self.cb_estado.addItem(str(e.descripcion), int(e.estado_receta_id))

        self.cb_estado.blockSignals(False)

    # -------------------------
    # search
    # -------------------------
    def _on_search_changed(self) -> None:
        self._search_timer.start(250)
